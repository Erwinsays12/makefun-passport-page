[![make.fun](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/c/the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Erwinsays12/makefun-passport-page/rank.svg)](https://make.fun/c/the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Erwinsays12/makefun-passport-page/reward.svg)](https://make.fun/c/the-passport-page-of-a-countr-2-20261121-0318)

# The Passport Page of a Country That Isn't There

An entry for the [make.fun bounty "The Passport Page of a Country That Isn't There"](https://make.fun/c/the-passport-page-of-a-countr-2-20261121-0318): a program that draws one invented passport spread for the fictional **Republic of Talveria** and writes it to `/output/entry.png`.

## What it draws

An open passport spread (1024x700 PNG, under 1 MiB), drawn entirely in code with the Python standard library — no images, no fonts, no network:

- **Data page** — coat of arms (star over three waves), bilingual field labels, a stylised engraved portrait of the holder, Mara Elin Aurell, a ferry captain from Vostra, her ink signature, and a machine-readable zone whose ICAO check digits are computed, not faked.
- **Visa page** — a Karthia tourist visa sticker with a real condition ("Holder must register with the Harbour Master within 72 hours of arrival. Employment prohibited."), a 45-taler fee stamp, and a consistent travel history: out of Talveria 28 AUG 2025, into Ostmar 29 AUG, out 11 SEP, home 12 SEP, out again 03 NOV, into Karthia 04 NOV. No stamp predates the passport's issue (12 MAR 2024) and every date agrees with the visa.
- **Security printing** — guilloche waves, a perforated document number, a faint watermark emblem, and paper fibre specks, all deterministic.

## Run it

```sh
python3 main.py
# writes /output/entry.png (1024x700 PNG, ~150 KB)
```

`main.py` needs only the Python 3.13 standard library (`zlib`, `struct`, `math`, `os`). It draws at 2x supersampling and downsamples for smooth edges, and finishes in about 4 seconds. The output is fully deterministic: same input, same bytes, every run.

## The country

Talveria is a small fjord republic on the cold sea between Ostmar and Karthia. Its passport is bilingual (Talverian/English), its harbour master collects a 12-taler fee, and its border officers warn travellers about the fog on the fjord road.

## License

MIT — see [LICENSE](LICENSE).
