import { Module } from '@nestjs/common';
import { LoggerService } from '../common/logger.service';
import { DrivesController } from './drives/drives.controller';
import { DrivesService } from './drives/drives.service';
import { FleetController } from './fleet/fleet.controller';
import { FleetService } from './fleet/fleet.service';
import { HealthController } from './health/health.controller';
import { PrismaModule } from './prisma.module';
import { ScoringController } from './scoring/scoring.controller';
import { ModelClientService } from './scoring/model-client.service';
import { ScoringService } from './scoring/scoring.service';

@Module({
  imports: [PrismaModule],
  controllers: [HealthController, FleetController, DrivesController, ScoringController],
  providers: [LoggerService, FleetService, DrivesService, ModelClientService, ScoringService],
})
export class AppModule {}
