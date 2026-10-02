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

## Symbols

| Symbol | Flick | Code |
|:--:|:--|:--|
| `.` | ↖ | `tl` |
| `,` | ↗ | `tr` |
| `?` | ↑ | `u` |
| `!` | ← | `l` |
| `'` | → | `r` |

Punctuation sticks to the word before it. The first letter of the text, and the first after `. ? !`, is a capital.

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

- **Wheel**: each tick up adds one, each tick down subtracts one (0 to 9). **Middle click** accepts the number as a character.
- **Right click** inserts a space. Middle click with nothing drawn and no number selected also inserts one.

## Buttons at a glance

| Control | Does |
|:--|:--|
| Flick | adds a direction to the letter |
| Middle click | accepts the letter, else the number, else a space |
| Left click | undoes the last flick, else backspace |
| Right click | space |
| Wheel | number 0-9 |
