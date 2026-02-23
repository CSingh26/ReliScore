import { describe, expect, it } from 'vitest';
import { cn } from '../lib/utils';

describe('cn utility', () => {
  it('merges class names and handles falsey values', () => {
    const className = cn('px-2', false && 'hidden', 'text-sm');
    expect(className).toContain('px-2');
    expect(className).toContain('text-sm');
  });
});
