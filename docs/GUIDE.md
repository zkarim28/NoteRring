# Ring Writer reference guide

*Generated from `alphabet.json` by `tools/make_guide.py`. Edit the alphabet, then run the script again.*

![Alphabet cheat sheet](alphabet.svg)

## The eight flicks

```
  ↖ tl     ↑ u     ↗ tr
  ← l      ·      → r
  ↙ bl     ↓ d     ↘ br
```

## Writing a letter

1. Flick the pad in the first direction, then lift your finger.
2. Flick the next direction, lift, and so on until the letter is spelled.
3. **Middle click** to accept it. The screen shows what you have drawn so far (for example `d r =L`) and which
   letters it could still become, so you can check before you accept.
4. Made a mistake? **Left click** undoes the last flick. With nothing drawn it deletes a character.

### When your flicks match no letter

The screen shows the best guess, for example `br u br tr =?` with `~W? mid=ok` and the tag `FIX`. **Nothing changes until you middle-click**:
middle click takes the guess, left click undoes the last flick so you can fix it yourself. It only guesses when one letter is clearly the best:
a flick that landed near a direction boundary counts as evidence, then any one flick off by 45 degrees, then one stray or missing flick (3+ flicks).
If several letters tie it shows them (`A/F/H?`) and middle click does nothing. A sequence that is already a letter is never replaced. `--no-suggest` turns it off.

Every flick is separate: the pause when you lift is what lets the same direction repeat (`d d r`).

## Letters

| Letter | Flicks | Codes |
|:--:|:--|:--|
| **A** | ↙ ↘ →<br>↙ ↘ ← | `bl br r`<br>`bl br l` |
| **B** | ↓ → ↙ → ↙ | `d r bl r bl` |
| **C** | ← ↓ → | `l d r` |
| **D** | ↓ → ↙ | `d r bl` |
| **E** | ↓ → → → | `d r r r` |
| **F** | ↓ → → | `d r r` |
| **G** | ↙ ↘ ↑ ← | `bl br u l` |
| **H** | ↓ ↓ →<br>↓ → ↓ | `d d r`<br>`d r d` |
| **I** | ↓ ← ← | `d l l` |
| **J** | → ↓ ↖<br>→ ← ↓ ↖ | `r d tl`<br>`r l d tl` |
| **K** | ↓ ↙ ↘ | `d bl br` |
| **L** | ↓ → | `d r` |
| **M** | ↓ ↑ ↓ ↑ ↓ | `d u d u d` |
| **N** | ↓ ↑ ↓ ↑ | `d u d u` |
| **O** | ← ↓ → ↑ | `l d r u` |
| **P** | ↓ ↘ ← | `d br l` |
| **Q** | ← ↓ → ↑ ↘ | `l d r u br` |
| **R** | ↓ ↘ ↙ ↘ | `d br bl br` |
| **S** | ↖ ↙ ↘ ↙ ↖<br>← ↓ → ↓ ← | `tl bl br bl tl`<br>`l d r d l` |
| **T** | ↓ ← | `d l` |
| **U** | ↘ ↗ ↓ | `br tr d` |
| **V** | ↘ ↗ | `br tr` |
| **W** | ↘ ↗ ↘ ↗ | `br tr br tr` |
| **X** | ↘ ↙ | `br bl` |
| **Y** | ↘ ↗ ↙ | `br tr bl` |
| **Z** | → ↙ → | `r bl r` |

## Punctuation (on the wheel)

Scroll the **wheel down** from rest to walk through the marks, **up** to go back (up past the first mark cancels). **Middle click** inserts the one shown.

```
. , ? ! ' " - : ; ( ) / @ & # $ % + = * _
```

Edit the `punctuation` list in `alphabet.json` to reorder or change them. `. , ? ! : ; ) %` stick to the word before them.
The first letter of the text, and the first after `. ? !`, is a capital.

## Letters one slip apart

A flick that is 45 degrees off turns one of these into the other, and no correction can notice because both are valid. Be careful with:

- **A** `bl br l` and **P** `d br l`
- **D** `d r bl` and **H** `d r d`
- **U** `br tr d` and **Y** `br tr bl`

## Letters that start other letters

You accept a letter yourself, so this is safe: just keep flicking for the longer one, or middle click to take the shorter.

- `l d r` (← ↓ →) is **C**, and also the start of O, Q, S
- `d r bl` (↓ → ↙) is **D**, and also the start of B
- `d r r` (↓ → →) is **F**, and also the start of E
- `d r` (↓ →) is **L**, and also the start of B, D, E, F, H
- `d u d u` (↓ ↑ ↓ ↑) is **N**, and also the start of M
- `l d r u` (← ↓ → ↑) is **O**, and also the start of Q
- `d l` (↓ ←) is **T**, and also the start of I
- `br tr` (↘ ↗) is **V**, and also the start of U, W, Y

## Numbers and spaces

- **Wheel up** from rest starts a number: each tick up adds one, each tick down subtracts one (0 to 9). **Middle click** accepts it as a character.
- **Right click** inserts a space. Middle click with nothing drawn and no number selected also inserts one.

## Buttons at a glance

| Control | Does |
|:--|:--|
| Flick | adds a direction to the letter |
| Middle click | accepts the letter (or the suggested one), else the number or mark, else a space |
| Left click | undoes the last flick, else backspace |
| Right click | space |
| Wheel up | number 0-9 |
| Wheel down | punctuation marks |
