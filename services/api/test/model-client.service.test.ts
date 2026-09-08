import { describe, expect, it, vi, beforeEach } from 'vitest';
const transport = vi.hoisted(() => ({get: vi.fn(), post: vi.fn()}));
vi.mock('axios', () => ({default: {create: () => transport}}));
import { ModelClientService } from '../src/modules/scoring/model-client.service';
const item = (id: string) => ({drive_id:id,day:'2026-01-01',features:{temperature:12}});
const score = (id: string) => ({drive_id:id,day:'2026-01-01',risk_score:.1,risk_bucket:'LOW',top_reasons:[],model_version:'test',scored_at:'2026-01-01T00:00:00Z'});
beforeEach(() => {vi.resetAllMocks();transport.get.mockResolvedValue({data:{features:['temperature'],model_version:'test',horizon_days:30}});});
describe('model batch contract', () => {
  it('chunks large fleets into bounded calls while preserving every score', async () => {
    transport.post.mockImplementation(async (_url, body) => ({data:body.items.map((row: {drive_id:string}) => score(row.drive_id))}));
    const result = await new ModelClientService().scoreBatch(Array.from({length:1001},(_,i)=>item(`d${i}`)));
    expect(result).toHaveLength(1001); expect(transport.post).toHaveBeenCalledTimes(2);
    expect(transport.post.mock.calls[0][1].items).toHaveLength(1000);
  });
  it.each(['foreign','missing','version','day'])('rejects %s response provenance', async (fault) => {
    const response = score('d1');
    if(fault==='foreign') response.drive_id='other';
    if(fault==='version') response.model_version='other';
    if(fault==='day') response.day='2026-01-02';
    transport.post.mockResolvedValue({data:fault==='missing'?[]:[response]});
    await expect(new ModelClientService().scoreBatch([item('d1')])).rejects.toThrow('Model service scoring call failed');
  });
});
