import { describe, expect, it } from 'vitest';

describe('health placeholder', () => {
  it('returns ok', () => {
    expect({ status: 'ok' }).toEqual({ status: 'ok' });
  });
});
