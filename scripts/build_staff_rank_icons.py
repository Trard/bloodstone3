#!/usr/bin/env python3
"""Draw the added staff ranks with the existing suffix pixel glyphs and frames."""
import argparse
from pathlib import Path
from PIL import Image

WHITE = (255, 255, 255, 255)


def glyphs(root, language, name, text):
    image = Image.open(root / language / f'{name}.png').convert('RGBA')
    spans = []
    for x in range(image.width):
        if any(image.getpixel((x, y)) == WHITE for y in range(image.height)):
            if spans and spans[-1][1] == x:
                spans[-1][1] += 1
            else:
                spans.append([x, x + 1])
    if len(spans) != len(text):
        raise ValueError(f'Unexpected source glyphs: {language}/{name}')
    output = {}
    for letter, (left, right) in zip(text, spans):
        mask = Image.new('L', (right - left, 5))
        for y in range(5):
            for x in range(right - left):
                if image.getpixel((left + x, y + 1)) == WHITE:
                    mask.putpixel((x, y), 255)
        output[letter] = mask
    return output


def draw_badge(reference, alphabet, text, shade=1.0):
    width = sum(alphabet[c].width if c != ' ' else 1 for c in text)
    width += sum(2 if c == '.' else 1 for c in text[:-1])
    badge = Image.new('RGBA', (width + 7, 7))
    fill = reference.getpixel((2, 3))
    edge = reference.getpixel((2, 0))
    shadow = reference.getpixel((0, 3))

    def tinted(color):
        return tuple(round(c * shade) for c in color[:3]) + (color[3],)

    for y in range(7):
        for x in range(badge.width):
            if x < 3:
                color = reference.getpixel((x, y))
            elif x >= badge.width - 3:
                color = reference.getpixel((reference.width - badge.width + x, y))
            else:
                color = edge if y in (0, 6) else fill
            badge.putpixel((x, y), tinted(color))
    text_mask = Image.new('L', badge.size)
    x = 3
    for letter in text:
        if letter == ' ':
            x += 2
            continue
        mask = alphabet[letter]
        text_mask.paste(mask, (x, 1))
        x += mask.width + (2 if letter == '.' else 1)
    badge.paste(tinted(shadow), (1, 0, badge.width + 1, 7), text_mask)
    badge.paste(WHITE, (0, 0, badge.width, 7), text_mask)
    return badge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.root / 'assets/minecraft/textures/font/suffixes'
    specs = {
        'ru': [('voenkor', 'ВОЕНКОР'), ('rank_production', 'ТЕХ.АДМИН'), ('glmoderator', 'ГЛ.МОДЕР'), ('senior_moderatior', 'СТ.МОДЕР')],
        'en': [('rank_production', 'TECH.ADMIN'), ('glmoderator', 'H.MOD'), ('voenkor', 'WARMASTER'), ('joker', 'JOKER')],
    }
    titles = {
        'ru': ('ГЛ.ВОЕНКОР', 'МЛ.ТЕХ.АДМИН'),
        'en': ('H.WAR MASTER', 'JR.TECH.ADMIN'),
    }
    for language, sources in specs.items():
        for name, text, reference, shade in [
            ('head_war_correspondent', titles[language][0], 'voenkor', 1.0),
            ('junior_technical_admin', titles[language][1], 'rank_production', 0.85),
        ]:
            reference_text = dict(sources)[reference]
            alphabet = glyphs(source, language, reference, reference_text)
            for other_name, other_text in sources:
                for letter, mask in glyphs(source, language, other_name, other_text).items():
                    alphabet.setdefault(letter, mask)
            frame = Image.open(source / language / f'{reference}.png').convert('RGBA')
            badge = draw_badge(frame, alphabet, text, shade)
            output = args.output / language / f'{name}.png'
            output.parent.mkdir(parents=True, exist_ok=True)
            badge.save(output, optimize=True)
            print(f'{language}/{name}: {badge.width} x {badge.height}')


if __name__ == '__main__':
    main()
