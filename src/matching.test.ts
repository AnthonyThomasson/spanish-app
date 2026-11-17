import { describe, expect, it } from 'vitest';
import { answerAlternatives, hasSpokenText, isCorrectAnswer, normalizeAnswer } from './matching';

// Word matching is the pre-existing behaviour. These tests pin it down so sentence support cannot change it.
describe('word matching (unchanged)', () => {
  it('ignores case, accents, punctuation and leading articles', () => {
    expect(normalizeAnswer('¡El Perro!')).toBe('perro');
    expect(normalizeAnswer('to run')).toBe('run');
    expect(normalizeAnswer('  Canción  ')).toBe('cancion');
  });

  it('splits alternatives on commas, semicolons, slashes and "or"', () => {
    expect(answerAlternatives('house; home, flat or apartment / dwelling')).toEqual([
      'house', 'home', 'flat', 'apartment', 'dwelling',
    ]);
  });

  it('treats a parenthetical as optional', () => {
    expect(answerAlternatives('car (m.)')).toEqual(['car m', 'car']);
    expect(isCorrectAnswer('car', 'car (m.)')).toBe(true);
  });

  it('accepts any alternative and rejects other words', () => {
    expect(isCorrectAnswer('home', 'house, home')).toBe(true);
    expect(isCorrectAnswer('garden', 'house, home')).toBe(false);
    expect(isCorrectAnswer('', 'house')).toBe(false);
  });

  it('does not apply sentence leniency to words', () => {
    expect(isCorrectAnswer('canto', 'yo canto')).toBe(false);
    expect(isCorrectAnswer("don't", 'do not')).toBe(false);
  });

  it('defaults to word matching and accepts an explicit word kind', () => {
    expect(isCorrectAnswer('home', 'house, home', 'word')).toBe(true);
    expect(isCorrectAnswer('canto', 'yo canto', 'word')).toBe(false);
  });
});

describe('sentence matching: alternatives', () => {
  it('does not split on commas, semicolons or "or"', () => {
    expect(isCorrectAnswer('We are tired, and you are hungry', 'We are tired, and you are hungry', 'sentence')).toBe(true);
    expect(isCorrectAnswer('we are tired', 'We are tired, and you are hungry', 'sentence')).toBe(false);
    expect(isCorrectAnswer('you are hungry', 'We are tired or you are hungry', 'sentence')).toBe(false);
    expect(isCorrectAnswer('we are tired', 'we are tired; you are hungry', 'sentence')).toBe(false);
  });

  it('is not fooled by "or" inside a sentence', () => {
    expect(isCorrectAnswer('do you want tea or coffee', 'Do you want tea or coffee?', 'sentence')).toBe(true);
    expect(isCorrectAnswer('coffee', 'Do you want tea or coffee?', 'sentence')).toBe(false);
  });

  it('splits only on " / "', () => {
    expect(isCorrectAnswer('he reads the paper', 'he reads the paper / she reads the paper', 'sentence')).toBe(true);
    expect(isCorrectAnswer('she reads the paper', 'he reads the paper / she reads the paper', 'sentence')).toBe(true);
    expect(isCorrectAnswer('he reads', 'he reads the paper / she reads the paper', 'sentence')).toBe(false);
  });

  it('does not split on a slash without surrounding spaces', () => {
    expect(isCorrectAnswer('he and she', 'he and/or she', 'sentence')).toBe(false);
    expect(isCorrectAnswer('he and or she', 'he and/or she', 'sentence')).toBe(true);
  });

  it('ignores punctuation, case and accents but keeps articles', () => {
    expect(isCorrectAnswer('donde esta la biblioteca', '¿Dónde está la biblioteca?', 'sentence')).toBe(true);
    expect(isCorrectAnswer('donde esta biblioteca', '¿Dónde está la biblioteca?', 'sentence')).toBe(false);
  });

  it('applies the same rules to conjugation cards', () => {
    expect(isCorrectAnswer('vos pensas', 'vos pensás', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('think', 'vos pensás', 'conjugation')).toBe(false);
  });

  it('treats the infinitive note on a Spanish conjugation prompt as optional', () => {
    expect(isCorrectAnswer('yo me siento', 'yo me siento (sentarse)', 'conjugation', 'es')).toBe(true);
    expect(isCorrectAnswer('me siento', 'yo me siento (sentarse)', 'conjugation', 'es')).toBe(true);
    expect(isCorrectAnswer('yo me siento sentarse', 'yo me siento (sentarse)', 'conjugation', 'es')).toBe(true);
    expect(isCorrectAnswer('yo me sientas', 'yo me siento (sentarse)', 'conjugation', 'es')).toBe(false);
  });

  it('accepts either alternative of a curated English conjugation prompt', () => {
    const expected = 'she is able / she can';
    expect(isCorrectAnswer('she is able', expected, 'conjugation', 'en')).toBe(true);
    expect(isCorrectAnswer('she can', expected, 'conjugation', 'en')).toBe(true);
    expect(isCorrectAnswer('she cans', expected, 'conjugation', 'en')).toBe(false);
    expect(isCorrectAnswer('she makes', 'she does / she makes (hacer)', 'conjugation', 'en')).toBe(true);
    expect(isCorrectAnswer('she does', 'she does / she makes (hacer)', 'conjugation', 'en')).toBe(true);
  });

  it('does not accept an empty answer', () => {
    expect(isCorrectAnswer('', 'we eat', 'sentence')).toBe(false);
    expect(isCorrectAnswer('   ', 'we eat', 'conjugation')).toBe(false);
  });
});

describe('sentence matching: Spanish subject pronouns', () => {
  it('accepts the pronoun to be dropped from the spoken answer', () => {
    expect(isCorrectAnswer('almuerzo', 'yo almuerzo', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('pensás', 'vos pensás', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('piensan', 'ellas piensan', 'conjugation')).toBe(true);
  });

  it('accepts a pronoun the expected answer does not have', () => {
    expect(isCorrectAnswer('yo almuerzo', 'almuerzo', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('nosotros cenamos temprano', 'cenamos temprano', 'sentence')).toBe(true);
  });

  it('rejects a different pronoun when both sides have one', () => {
    expect(isCorrectAnswer('ellos piensan', 'ellas piensan', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('yo canta', 'ella canta', 'conjugation')).toBe(false);
  });

  it('still requires the verb form to match', () => {
    expect(isCorrectAnswer('yo almuerzas', 'yo almuerzo', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('almorzamos', 'yo almuerzo', 'conjugation')).toBe(false);
  });

  it('treats él with and without its accent the same', () => {
    expect(isCorrectAnswer('él duerme', 'él duerme', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('el duerme', 'él duerme', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('duerme', 'él duerme', 'conjugation')).toBe(true);
  });

  it('treats usted and Ud. as the same, and ustedes and Uds.', () => {
    expect(isCorrectAnswer('usted come', 'Ud. come', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('Ud come', 'usted come', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('ustedes comen', 'Uds. comen', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('come', 'Ud. come', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('ustedes come', 'Ud. come', 'conjugation')).toBe(false);
  });

  it('accepts nosotras for nosotros', () => {
    expect(isCorrectAnswer('nosotras vivimos', 'nosotros vivimos', 'conjugation')).toBe(true);
  });

  it('only drops "él" as a pronoun when it is accented; an unaccented "el" is the article', () => {
    expect(isCorrectAnswer('duerme', 'él duerme', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('él duerme', 'duerme', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('el duerme', 'duerme', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('libro rojo', 'el libro rojo', 'sentence')).toBe(false);
    expect(isCorrectAnswer('el libro rojo', 'libro rojo', 'sentence')).toBe(false);
    expect(isCorrectAnswer('el libro rojo', 'el libro rojo', 'sentence')).toBe(true);
  });

  it('does not strip a lone pronoun', () => {
    expect(isCorrectAnswer('ella', 'ella', 'sentence')).toBe(true);
    expect(isCorrectAnswer('', 'ella', 'sentence')).toBe(false);
    expect(isCorrectAnswer('yo', 'ella', 'sentence')).toBe(false);
  });

  it('only treats a leading pronoun as optional', () => {
    expect(isCorrectAnswer('canta ella', 'ella canta', 'sentence')).toBe(false);
    expect(isCorrectAnswer('hoy yo canto', 'hoy canto', 'sentence')).toBe(false);
  });
});

describe('sentence matching: English contractions', () => {
  it.each([
    ["I don't know", 'I do not know'],
    ["he doesn't sleep", 'he does not sleep'],
    ["I'm happy", 'I am happy'],
    ["he's tall", 'he is tall'],
    ["she's tall", 'she is tall'],
    ["it's cold", 'it is cold'],
    ["we're ready", 'we are ready'],
    ["they're late", 'they are late'],
    ["you're right", 'you are right'],
    ["it isn't open", 'it is not open'],
    ["they aren't here", 'they are not here'],
    ["I can't swim", 'I can not swim'],
    ["I can't swim", 'I cannot swim'],
    ["we won't go", 'we will not go'],
  ])('treats %s and %s as equal', (a, b) => {
    expect(isCorrectAnswer(a, b, 'sentence')).toBe(true);
    expect(isCorrectAnswer(b, a, 'sentence')).toBe(true);
  });

  it('handles curly apostrophes and capitals', () => {
    expect(isCorrectAnswer('I’m Happy', 'I am happy', 'sentence')).toBe(true);
    expect(isCorrectAnswer("We're Ready", 'we are ready', 'conjugation')).toBe(true);
  });

  it('does not make unrelated words equal', () => {
    expect(isCorrectAnswer("he's tall", 'she is tall', 'sentence')).toBe(false);
    expect(isCorrectAnswer("I don't know", 'I know', 'sentence')).toBe(false);
  });

  it('does not expand contractions for word cards', () => {
    expect(isCorrectAnswer("don't", 'do not')).toBe(false);
  });
});

describe('sentence matching: disambiguation tags', () => {
  it('accepts a tagged English answer with or without the tag', () => {
    expect(isCorrectAnswer('sing', 'Sing (vos).', 'sentence')).toBe(true);
    expect(isCorrectAnswer('sing vos', 'Sing (vos).', 'sentence')).toBe(true);
    expect(isCorrectAnswer('where do you work', 'Where do you work (Ud.)?', 'sentence')).toBe(true);
    expect(isCorrectAnswer('i want to call them', 'I want to call them (m.).', 'sentence')).toBe(true);
    expect(isCorrectAnswer('it was cold', 'It was cold (Sp. fue frío).', 'sentence')).toBe(true);
  });

  it('still rejects a different sentence', () => {
    expect(isCorrectAnswer('eat', 'Sing (vos).', 'sentence')).toBe(false);
  });
});

describe('sentence matching: parentheticals', () => {
  it('treats a trailing or inner parenthetical as optional', () => {
    expect(isCorrectAnswer('you think', 'you (formal) think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('they think', 'they (f.) think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('you eat', 'you eat (formal)', 'conjugation')).toBe(true);
  });

  it('also accepts the parenthetical text when it is said', () => {
    expect(isCorrectAnswer('you formal think', 'you (formal) think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('they f think', 'they (f.) think', 'conjugation')).toBe(true);
  });

  it('handles several parentheticals', () => {
    expect(isCorrectAnswer('you think', 'you (formal) think (a lot)', 'sentence')).toBe(true);
    expect(isCorrectAnswer('you think a lot', 'you (formal) think (a lot)', 'sentence')).toBe(true);
    expect(isCorrectAnswer('you formal think', 'you (formal) think (a lot)', 'sentence')).toBe(true);
  });

  it('does not treat other words as the parenthetical', () => {
    expect(isCorrectAnswer('you informal think', 'you (formal) think', 'conjugation')).toBe(false);
  });
});

describe('sentence matching: formal and plural labels', () => {
  it('does not need the label to be said', () => {
    expect(isCorrectAnswer('where are you from', 'Formal: Where are you from?', 'sentence')).toBe(true);
    expect(isCorrectAnswer("don't yell", "Plural: Don't yell.", 'sentence')).toBe(true);
    expect(isCorrectAnswer('you are', 'Formal: you are (estar)', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('you can', 'Formal: you are able / you can', 'conjugation')).toBe(true);
  });

  it('accepts the label when it is said', () => {
    expect(isCorrectAnswer('formal where are you from', 'Formal: Where are you from?', 'sentence')).toBe(true);
    expect(isCorrectAnswer('formal you are', 'Formal: you are (estar)', 'conjugation')).toBe(true);
  });

  it('still needs the rest of the answer', () => {
    expect(isCorrectAnswer('formal', 'Formal: you are', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('where are you', 'Formal: Where are you from?', 'sentence')).toBe(false);
    expect(isCorrectAnswer('plural you are', 'Formal: you are', 'conjugation')).toBe(false);
  });

  it('only treats a label at the very start as one', () => {
    expect(isCorrectAnswer('it is formal', 'It is formal.', 'sentence')).toBe(true);
    expect(isCorrectAnswer('it is', 'It is formal.', 'sentence')).toBe(false);
  });
});

describe('sentence matching: long-sentence tolerance', () => {
  const english = 'we eat dinner with the grandmother every night';
  const spanish = 'cenamos con mi abuela que vive en una casa vieja';

  it('forgives a missing or extra small function word in a sentence of six or more words', () => {
    expect(isCorrectAnswer('we eat dinner with grandmother every night', english, 'sentence')).toBe(true);
    expect(isCorrectAnswer('we eat dinner with the the grandmother every night', english, 'sentence')).toBe(true);
    expect(isCorrectAnswer('we eat dinner with the grandmother every night to', english, 'sentence')).toBe(true);
    expect(isCorrectAnswer('cenamos con mi abuela vive en una casa vieja', spanish, 'sentence')).toBe(true); // que
    expect(isCorrectAnswer('cenamos con mi abuela que vive en casa vieja', spanish, 'sentence')).toBe(true); // una
    expect(isCorrectAnswer('cenamos con mi abuela que vive en una casa de vieja', spanish, 'sentence')).toBe(true); // de added
  });

  it('forgives an extra function word the expected answer lacks, but not an extra content word', () => {
    expect(isCorrectAnswer('we eat dinner with the grandmother every single night', 'we eat dinner with the grandmother every night', 'sentence')).toBe(false);
    expect(isCorrectAnswer('we eat dinner with a grandmother every night', 'we eat dinner with grandmother every night', 'sentence')).toBe(true);
    expect(isCorrectAnswer('I think that we eat dinner at home now', 'I think we eat dinner at home now', 'sentence')).toBe(true);
    expect(isCorrectAnswer('pienso que comemos juntos en casa hoy', 'pienso comemos juntos en casa hoy', 'sentence')).toBe(true);
  });

  it('never forgives a dropped or added first word', () => {
    expect(isCorrectAnswer('the we eat dinner with grandmother every night', 'we eat dinner with grandmother every night', 'sentence')).toBe(false);
    expect(isCorrectAnswer('we eat dinner with grandmother every night', 'the we eat dinner with grandmother every night', 'sentence')).toBe(false);
    expect(isCorrectAnswer('abuela que vive en una casa vieja hoy', 'una abuela que vive en una casa vieja hoy', 'sentence')).toBe(false);
  });

  it('never forgives a different word, even a close one', () => {
    expect(isCorrectAnswer('we eat lunch with the grandmother every night', english, 'sentence')).toBe(false);
    expect(isCorrectAnswer('we eat dinner with the grandfather every night', english, 'sentence')).toBe(false);
    expect(isCorrectAnswer('we eat dinner with the grandmother every day', english, 'sentence')).toBe(false);
  });

  it.each([
    // Spanish articles: a swapped or dropped definite article is a gender or meaning error.
    ['el casa es grande y muy bonita hoy', 'la casa es grande y muy bonita hoy'],
    ['ella casa es grande y muy bonita hoy', 'la casa es grande y muy bonita hoy'],
    ['la libro es grande y muy bonito hoy', 'el libro es grande y muy bonito hoy'],
    ['la libro es grande y muy bonito hoy', 'él libro es grande y muy bonito hoy'],
    ['casa es grande y muy bonita hoy', 'la casa es grande y muy bonita hoy'],
    ['la casa es grande y muy bonita hoy', 'casa es grande y muy bonita hoy'],
    ['los libros son grandes y muy bonitos hoy', 'las libros son grandes y muy bonitos hoy'],
    ['voy a ver los libros nuevos de mi hermana hoy', 'voy a ver libros nuevos de mi hermana hoy'],
    // Object pronouns (clitics).
    ['yo veo la casa de mi abuela todos los dias', 'yo la veo la casa de mi abuela todos los dias'],
    ['yo veo a mi abuela todos los dias en casa', 'yo la veo a mi abuela todos los dias en casa'],
    ['ella ve a mi abuela todos los dias en casa', 'ella le ve a mi abuela todos los dias en casa'],
    ['nosotros vemos a mis tios todos los dias hoy', 'nosotros los vemos a mis tios todos los dias hoy'],
    ['yo lo veo a mi abuelo todos los dias en casa', 'yo la veo a mi abuelo todos los dias en casa'],
    ['unos libros son grandes y muy bonitos hoy', 'libros son grandes y muy bonitos hoy'],
    ['cenamos con mi abuela que vive en unos casa vieja', 'cenamos con mi abuela que vive en una casa vieja'],
  ])('rejects %s for %s', (spoken, expected) => {
    expect(isCorrectAnswer(spoken, expected, 'sentence')).toBe(false);
    expect(isCorrectAnswer(spoken, expected, 'conjugation')).toBe(false);
  });

  it('does not let a stripped pronoun hide a different article or a dropped small word', () => {
    expect(isCorrectAnswer('cenamos con abuela que vive en una casa vieja', 'nosotros cenamos con mi abuela que vive en una casa vieja', 'sentence')).toBe(false);
    expect(isCorrectAnswer('cenamos con mi abuela vive en una casa vieja', 'nosotros cenamos con mi abuela que vive en una casa vieja', 'sentence')).toBe(false);
    expect(isCorrectAnswer('nosotros cenamos con mi abuela que vive en una casa vieja', 'nosotros cenamos con mi abuela vive en una casa vieja', 'sentence')).toBe(true);
    expect(isCorrectAnswer('cenamos con mi abuela que vive en una casa vieja', 'nosotros cenamos con mi abuela que vive en una casa vieja', 'sentence')).toBe(true);
  });

  it.each([
    ['we have lunch at noon every day today', 'I have lunch at noon every day today', 'wrong person'],
    ['I have lunch at noon every day today', 'we have lunch at noon every day today', 'wrong person'],
    ['como pan con queso todos los dias', 'comes pan con queso todos los dias', 'wrong verb form'],
    ['yesterday he went to the market with his friend', 'yesterday he goes to the market with his friend', 'wrong tense'],
    ['they went to the market early every morning', 'they go to the market early every morning', 'wrong tense'],
    ['she has three brothers and one sister now', 'she has four brothers and one sister now', 'wrong number'],
    ['she has 3 brothers and one sister now', 'she has 4 brothers and one sister now', 'wrong digit'],
    ['I called her after the meeting this morning', 'I called him after the meeting this morning', 'wrong pronoun'],
    ['we went there with the whole family today', 'we went there without the whole family today', 'wrong meaning word'],
    ['tengo un amigo muy simpatico en mi clase', 'tengo un amiga muy simpatico en mi clase', 'wrong gender'],
    ['la amiga de mi hermana vive en la ciudad', 'la amigo de mi hermana vive en la ciudad', 'wrong gender'],
    ['I do not want to go to the party tonight', 'I do want to go to the party tonight', 'negation'],
    ['I do want to go to the party tonight', 'I do not want to go to the party tonight', 'negation'],
    ['ellos no quieren ir a la fiesta de hoy', 'ellos quieren ir a la fiesta de hoy', 'negation'],
  ])('rejects %s for %s (%s)', (spoken, expected) => {
    expect(isCorrectAnswer(spoken, expected, 'sentence')).toBe(false);
  });

  it('rejects the same slips on conjugation cards', () => {
    expect(isCorrectAnswer('vos pensas en la casa de tus abuelos hoy', 'vos pensas en la casa de mis abuelos hoy', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('ellos piensan en la casa de sus abuelos hoy', 'ellas piensan en la casa de sus abuelos hoy', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('we think about the house of our grandparents today', 'I think about the house of our grandparents today', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('you think about the house of our grandparents today', 'you thought about the house of our grandparents today', 'conjugation')).toBe(false);
  });

  it('forgives a function word on conjugation cards too', () => {
    expect(isCorrectAnswer('vos pensas en una casa de tus abuelos hoy', 'vos pensas en casa de tus abuelos hoy', 'conjugation')).toBe(true);
  });

  it('is exact for sentences under six words', () => {
    expect(isCorrectAnswer('we eat with grandmother', 'we eat with the grandmother', 'sentence')).toBe(false);
    expect(isCorrectAnswer('she reads a book now', 'she reads the book now', 'sentence')).toBe(false);
  });

  it('applies to whichever alternative is closest', () => {
    const expected = 'they walk to school every morning / they go to school on foot every morning';
    expect(isCorrectAnswer('they walk every morning', expected, 'sentence')).toBe(false);
    expect(isCorrectAnswer('they walk school every morning', expected, 'sentence')).toBe(true);
    expect(isCorrectAnswer('they walk to the school every morning', expected, 'sentence')).toBe(true);
    expect(isCorrectAnswer('they go to the school on foot every morning', expected, 'sentence')).toBe(true);
  });

  it('keeps a slash inside parentheses part of the parenthetical', () => {
    expect(isCorrectAnswer('you think', 'you (formal / informal) think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('he thinks', 'he thinks / she thinks', 'conjugation')).toBe(true);
  });

  it('never applies to word cards', () => {
    expect(isCorrectAnswer('we eat dinner with grandmother every night', english, 'word')).toBe(false);
  });
});

describe('sentence matching: more contractions', () => {
  it.each([
    ["what's your name", 'what is your name'],
    ["that's my house", 'that is my house'],
    ["there's a book here", 'there is a book here'],
    ["where's the station", 'where is the station'],
    ["who's at the door", 'who is at the door'],
    ["here's the key", 'here is the key'],
    ["let's go home", 'let us go home'],
    ["how's your mother", 'how is your mother'],
    ["I'd like some water", 'I would like some water'],
    ["she'd love a coffee", 'she would love a coffee'],
    ["we'd prefer tea", 'we would prefer tea'],
    ["they haven't eaten", 'they have not eaten'],
    ["he wouldn't go", 'he would not go'],
  ])('treats %s and %s as equal', (a, b) => {
    expect(isCorrectAnswer(a, b, 'sentence')).toBe(true);
    expect(isCorrectAnswer(b, a, 'sentence')).toBe(true);
  });

  it('reads curly apostrophes in the new contractions', () => {
    expect(isCorrectAnswer('I’d like water', 'I would like water', 'sentence')).toBe(true);
    expect(isCorrectAnswer('let’s go home', 'let us go home', 'sentence')).toBe(true);
  });

  it('does not guess at the ambiguous \'d', () => {
    expect(isCorrectAnswer("I'd gone home", 'I would gone home', 'sentence')).toBe(false);
    expect(isCorrectAnswer("I'd gone home", 'I had gone home', 'sentence')).toBe(false);
  });
});

describe('sentence matching: numbers', () => {
  it('matches digits against number words', () => {
    expect(isCorrectAnswer('I have 2 brothers', 'I have two brothers', 'sentence')).toBe(true);
    expect(isCorrectAnswer('I have two brothers', 'I have 2 brothers', 'sentence')).toBe(true);
    expect(isCorrectAnswer('tengo 3 hermanas', 'tengo tres hermanas', 'sentence')).toBe(true);
    expect(isCorrectAnswer('she is 21 years old', 'she is twenty-one years old', 'sentence')).toBe(true);
    expect(isCorrectAnswer('hay 35 alumnos', 'hay treinta y cinco alumnos', 'sentence')).toBe(true);
    expect(isCorrectAnswer('it costs 1,200 pesos', 'it costs one thousand two hundred pesos', 'sentence')).toBe(true);
  });

  it('does not match different numbers', () => {
    expect(isCorrectAnswer('I have 3 brothers', 'I have two brothers', 'sentence')).toBe(false);
    expect(isCorrectAnswer('she is 22 years old', 'she is twenty-one years old', 'sentence')).toBe(false);
  });

  it('does not read English "once" as eleven in a sentence, but does in Spanish', () => {
    expect(isCorrectAnswer('we go there 11 times a week', 'we go there once times a week', 'sentence', 'en')).toBe(false);
    expect(isCorrectAnswer('we go there once a week', 'we go there once a week', 'sentence', 'en')).toBe(true);
    expect(isCorrectAnswer('tengo 11 gatos en mi casa', 'tengo once gatos en mi casa', 'sentence', 'es')).toBe(true);
    expect(isCorrectAnswer('tengo 11 gatos en mi casa', 'tengo once gatos en mi casa', 'sentence', 'en')).toBe(false);
  });

  it('reads "a hundred" and "a thousand" in sentences', () => {
    expect(isCorrectAnswer('it costs 100 pesos', 'it costs a hundred pesos', 'sentence', 'en')).toBe(true);
    expect(isCorrectAnswer('it costs a thousand pesos', 'it costs 1000 pesos', 'sentence', 'en')).toBe(true);
    expect(isCorrectAnswer('it costs 100 pesos', 'it costs a thousand pesos', 'sentence', 'en')).toBe(false);
  });

  it('works on conjugation cards too', () => {
    expect(isCorrectAnswer('we have 2', 'we have two', 'conjugation')).toBe(true);
  });
});

describe('sentence matching: you all', () => {
  it('accepts "you guys" and "y\'all" for "you all"', () => {
    expect(isCorrectAnswer('you guys think', 'you all think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer("y'all think", 'you all think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('yall think', 'you all think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('Y’all think', 'you all think', 'conjugation')).toBe(true);
    expect(isCorrectAnswer('you all think', 'you guys think', 'conjugation')).toBe(true);
  });

  it('still tells you all from the singular and the formal', () => {
    expect(isCorrectAnswer('you think', 'you all think', 'conjugation')).toBe(false);
    expect(isCorrectAnswer('you all think', 'you (formal) think', 'conjugation')).toBe(false);
  });
});

describe('word matching: numbers', () => {
  it('accepts digits for a number word and number words for digits', () => {
    expect(isCorrectAnswer('2', 'two')).toBe(true);
    expect(isCorrectAnswer('4', 'cuatro')).toBe(true);
    expect(isCorrectAnswer('cuatro', '4')).toBe(true);
    expect(isCorrectAnswer('forty two', '42')).toBe(true);
    expect(isCorrectAnswer('42', 'forty-two')).toBe(true);
    expect(isCorrectAnswer('21', 'veintiuno')).toBe(true);
    expect(isCorrectAnswer('100', 'one hundred')).toBe(true);
    expect(isCorrectAnswer('2', 'two (2)')).toBe(true);
  });

  it('rejects a different number', () => {
    expect(isCorrectAnswer('3', 'two')).toBe(false);
    expect(isCorrectAnswer('tres', 'cuatro')).toBe(false);
    expect(isCorrectAnswer('4', 'forty')).toBe(false);
  });

  it('does not match two number words by value across languages', () => {
    expect(isCorrectAnswer('eleven', 'once')).toBe(false);
    expect(isCorrectAnswer('ten', 'diez')).toBe(false);
    expect(isCorrectAnswer('one', 'uno')).toBe(false);
    expect(isCorrectAnswer('once', 'once')).toBe(true);
  });

  it('treats "once" as eleven only for a Spanish answer', () => {
    expect(isCorrectAnswer('11', 'once', 'word', 'es')).toBe(true);
    expect(isCorrectAnswer('once', '11', 'word', 'es')).toBe(true);
    expect(isCorrectAnswer('11', 'once', 'word', 'en')).toBe(false);
    expect(isCorrectAnswer('11', 'once')).toBe(false);
    expect(isCorrectAnswer('11', 'eleven', 'word', 'en')).toBe(true);
    expect(isCorrectAnswer('once', 'once', 'word', 'en')).toBe(true);
  });

  it('accepts "a hundred" and "a thousand"', () => {
    expect(isCorrectAnswer('100', 'a hundred')).toBe(true);
    expect(isCorrectAnswer('a hundred', '100')).toBe(true);
    expect(isCorrectAnswer('1000', 'a thousand', 'word', 'en')).toBe(true);
    expect(isCorrectAnswer('a thousand', '1000', 'word', 'en')).toBe(true);
    expect(isCorrectAnswer('100', 'a thousand')).toBe(false);
  });

  it('does not turn other words into numbers', () => {
    expect(isCorrectAnswer('2', 'cat')).toBe(false);
    expect(isCorrectAnswer('two', 'second')).toBe(false);
    expect(isCorrectAnswer('2', 'two cats')).toBe(false);
  });

  it('still takes a number word among other alternatives', () => {
    expect(isCorrectAnswer('1', 'one, a single')).toBe(true);
    expect(isCorrectAnswer('single', 'one, a single')).toBe(true);
  });
});

describe('hasSpokenText', () => {
  it('is false when recognition returned nothing', () => {
    expect(hasSpokenText([])).toBe(false);
  });

  it('is false when every transcript is blank or whitespace', () => {
    expect(hasSpokenText(['', '   ', '\n\t'])).toBe(false);
  });

  it('is true when any transcript has text', () => {
    expect(hasSpokenText(['', 'gato'])).toBe(true);
  });
});
