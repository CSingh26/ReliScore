import assert from 'node:assert/strict';
import { PrismaClient } from '@prisma/client';
import { ScoringService } from '../src/modules/scoring/scoring.service';
import { ModelClientService } from '../src/modules/scoring/model-client.service';
import { DrivesService } from '../src/modules/drives/drives.service';
import { FleetService } from '../src/modules/fleet/fleet.service';

async function main() {
  const url = process.env.DATABASE_URL ?? '';
  assert.ok(url.includes('/reliscore_portfolio_test'), 'Use an isolated reliscore_portfolio_test database');
  const db = new PrismaClient();
  const target = new Date('2026-03-01');
  const ids = ['SYNTHETIC-low', 'SYNTHETIC-high', 'SYNTHETIC-stale', 'SYNTHETIC-failed'];
  const model = new ModelClientService();
  try {
    await db.drive.deleteMany({where:{driveId:{in:ids}}});
    for (const [index,driveId] of ids.entries()) {
      await db.drive.create({data:{driveId,model:'SYNTHETIC SOFTWARE FIXTURE',datacenter:'Isolated test database',capacityBytes:1000n,firstSeen:new Date('2025-01-01'),lastSeen:target}});
      const rows = Array.from({length:40},(_,i)=>({driveId,day:new Date(target.getTime()-(39-i)*86400000),smart5:index*10,smart197:index*5,temperature:30+index,isFailedToday:driveId.endsWith('failed')&&i===39}));
      await db.telemetryDaily.createMany({data:driveId.endsWith('stale')?rows.slice(0,-1):rows});
    }
    // Simulate a previously generated feature that must not be scored after failure.
    await db.featuresDaily.create({data:{driveId:'SYNTHETIC-failed',day:target,featureVector:{age_days:20}}});
    const service = new ScoringService(db as never,{info:()=>{}} as never,model);
    const result = await service.runScoringJob('2026-03-01');
    assert.equal(result.generatedFeatures,2); assert.equal(result.storedPredictions,2);
    const persisted = await db.prediction.findMany({where:{day:target},orderBy:{driveId:'asc'}});
    assert.equal(persisted.length,2);
    assert.ok(persisted.every(p=>p.modelVersion==='synthetic-software-fixture-v1'));
    assert.equal(await db.prediction.count({where:{driveId:{in:['SYNTHETIC-stale','SYNTHETIC-failed']}}}),0);
    await service.runScoringJob('2026-03-01');
    assert.equal(await db.prediction.count({where:{day:target}}),2,'idempotent rerun');
    // Add a historical model version: counts must remain per drive, not per model row.
    const p = persisted[0];
    await db.prediction.create({data:{driveId:p.driveId,day:target,modelVersion:'obsolete-synthetic-fixture',riskScore:.99,riskBucket:'HIGH',reasonCodes:[],scoredAt:new Date('2020-01-01')}});
    const summary = await new FleetService(db as never).getSummary('2026-03-01');
    assert.equal(summary.drivesScoredToday,2,'one latest score per drive/day');
    const filtered = await new DrivesService(db as never).listDrives({risk:'HIGH',page:1,pageSize:10});
    assert.equal(filtered.total,0,'historical high score must not put a currently low drive in the high filter');
    const detail = await new DrivesService(db as never).getDriveDetails(p.driveId);
    assert.equal(detail.riskHistory.at(-1)?.modelVersion,'synthetic-software-fixture-v1','detail picks latest scored model per day');
    console.log('PASS: real PostgreSQL + HTTP model scoring, eligibility, idempotency and latest-version fleet count');
  } finally {
    if(process.env.KEEP_SYNTHETIC_FIXTURE!=='true') await db.drive.deleteMany({where:{driveId:{in:ids}}});
    await db.$disconnect();
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
