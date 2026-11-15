import { describe, expect, it } from 'vitest';
import { canonicalizeNumbers, numberValue } from './numbers';

const canon = (text: string) => canonicalizeNumbers(text.split(' ')).join(' ');

describe('canonicalizeNumbers', () => {
  it('turns English number words into digits', () => {
    expect(canon('zero')).toBe('0');
    expect(canon('seven')).toBe('7');
    expect(canon('seventeen')).toBe('17');
    expect(canon('forty two')).toBe('42');
    expect(canon('ninety nine')).toBe('99');
    expect(canon('one hundred')).toBe('100');
    expect(canon('a hundred')).toBe('a 100');
    expect(canon('two hundred and five')).toBe('205');
    expect(canon('three thousand four hundred twelve')).toBe('3412');
    expect(canon('one hundred thousand')).toBe('100000');
    expect(canon('two million five hundred thousand')).toBe('2500000');
  });

  it('turns Spanish number words into digits', () => {
    expect(canon('cero')).toBe('0');
    expect(canon('cuatro')).toBe('4');
    expect(canon('quince')).toBe('15');
    expect(canon('veintiuno')).toBe('21');
    expect(canon('veintidos')).toBe('22');
    expect(canon('treinta y cinco')).toBe('35');
    expect(canon('cien')).toBe('100');
    expect(canon('ciento diez')).toBe('110');
    expect(canon('doscientos cincuenta y uno')).toBe('251');
    expect(canon('mil')).toBe('1000');
    expect(canon('dos mil veinte')).toBe('2020');
  });

  it('leaves digits and other words alone', () => {
    expect(canon('42')).toBe('42');
    expect(canon('we have 3 cats')).toBe('we have 3 cats');
  });

  it('keeps separate numbers separate', () => {
    expect(canon('one two')).toBe('1 2');
    expect(canon('twenty thirty')).toBe('20 30');
    expect(canon('three four five')).toBe('3 4 5');
    expect(canon('treinta uno')).toBe('31'); // tens then unit is one number
    expect(canon('dos tres')).toBe('2 3');
  });

  it('does not swallow a connector that does not join two number words', () => {
    expect(canon('four and a half')).toBe('4 and a half');
    expect(canon('tres y media')).toBe('3 y media');
    expect(canon('twenty and one')).toBe('20 and 1');
  });

  it('converts numbers inside a sentence', () => {
    expect(canon('we have twenty one cats and three dogs')).toBe('we have 21 cats and 3 dogs');
  });
});

describe('numberValue', () => {
  it('reads a whole answer that is one number, in digits or words', () => {
    expect(numberValue('2')).toBe(2);
    expect(numberValue('two')).toBe(2);
    expect(numberValue('Forty-two')).toBe(42);
    expect(numberValue('cuarenta y dos')).toBe(42);
    expect(numberValue('1,000')).toBe(1000);
    expect(numberValue('¡Cuatro!')).toBe(4);
  });

  it('is null for anything else', () => {
    expect(numberValue('cat')).toBeNull();
    expect(numberValue('two cats')).toBeNull();
    expect(numberValue('one two')).toBeNull();
    expect(numberValue('')).toBeNull();
  });
});
