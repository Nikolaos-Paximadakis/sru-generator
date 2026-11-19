# Disclaimer

**sru-generator is not tax advice, and it is not affiliated with, endorsed by or
supported by Skatteverket (the Swedish Tax Agency).**

## What it does, and what it leaves to you

sru-generator turns figures you supply into the SRU files that Skatteverket's
e-service imports for bilaga K4. It applies the file format and the rounding rules
described in Skatteverket's published help text, as the authors understood them at
the time of each release. Skatteverket can change those rules and the file format at
any time.

It does **not** decide anything about your taxes. In particular, it does not fetch
your trades, convert foreign currency, choose a cost-basis method (genomsnittsmetoden
or schablonmetoden), decide which K4 section an asset belongs in, or check that your
input is complete or correct. Those are your inputs and your decisions.

## Your responsibility

The person who submits a tax declaration is responsible for its content, whichever
tool produced the file. Skatteverket can charge a tax surcharge (skattetillägg) for
incorrect information. Before you sign:

- check every row and total of the imported K4 in Skatteverket's e-service;
- keep the records the figures came from (broker statements, purchase history);
- ask a qualified tax adviser, or Skatteverket, if you are unsure how something
  should be reported.

## No warranty, no liability

The software is provided "as is", without warranty of any kind, under the
[MIT License](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/LICENSE).
To the fullest extent permitted by law, the authors and contributors are not liable
for errors in any tax declaration, for tax surcharges, interest or penalties, or for
any other loss or damage arising from the use of this software.

---

## Ansvarsfriskrivning (svenska)

**sru-generator är inte skatterådgivning och har ingen koppling till Skatteverket.
Programmet är varken godkänt eller stöttat av Skatteverket.**

Programmet omvandlar uppgifter som du själv lämnar till SRU-filer för bilaga K4. Det
tillämpar filformatet och avrundningsreglerna i Skatteverkets publicerade
hjälptexter, så som upphovspersonerna har tolkat dem vid varje version. Reglerna och
filformatet kan ändras.

Programmet fattar inga beslut om din beskattning. Det hämtar inte dina affärer,
räknar inte om utländsk valuta, väljer inte metod för omkostnadsbeloppet och
kontrollerar inte att dina uppgifter är fullständiga eller riktiga.

Den som lämnar deklarationen ansvarar för innehållet, oavsett vilket verktyg som har
skapat filen. Skatteverket kan ta ut skattetillägg för oriktiga uppgifter. Granska
varje rad och summa i Skatteverkets e-tjänst innan du skriver under, och spara
underlagen.

Programmet tillhandahålls i befintligt skick ("as is"), utan garantier av något slag,
enligt MIT-licensen. Upphovspersonerna och bidragsgivarna ansvarar, i den utsträckning
lagen tillåter, inte för fel i deklarationer, skattetillägg, ränta eller annan skada
som uppstår genom användning av programmet.
