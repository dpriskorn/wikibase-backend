This is a list of all data types with the corresponding value types available on this installation.

## Commons media (string)

Link to files stored at Wikimedia Commons. When a value is entered, the “File” namespace on Commons will be searched for matching files.

**Value type:** `string`

## Geographic shape (string)

Link to geographic map data stored on Wikimedia Commons (or another configured wiki).

**Value type:** `string`

## Tabular data (string)

Link to tabular data stored on Wikimedia Commons (or another configured wiki).

**Value type:** `string`

## URL (string)

Literal data field for a URL. URLs are restricted to the protocols supported for external links in wikitext.

**Value type:** `string`

## External identifier (string)

Literal data field for an external identifier. External identifiers may automatically be linked to an authoritative resource for display.

**Value type:** `string`

## Item (Wikibase entity id)

Link to other Items on the project. When a value is entered, the project’s “Item” namespace will be searched for matching Items.

**Value type:** `wikibase-entityid`

## Property (Wikibase entity id)

Link to Properties on the project. When a value is entered, the project’s “Property” namespace will be searched for matching Properties.

**Value type:** `wikibase-entityid`

## Globe coordinate (globe coordinate)

Literal data for a geographical position given as a latitude–longitude pair in degrees/minutes/seconds or decimal degrees for the given stellar body. Defaults to Earth and WGS84. Includes resolution and range.

- **latitude** – implicit first part of the coordinate string (float, DMS, DM, DD); direction given by sign or N/S  
- **longitude** – implicit second part of the coordinate string (float, DMS, DM, DD); direction given by sign or E/W  
- **globe** – explicit value identifying the stellar body (defaults to Earth)  
- **precision** – numeric precision of the coordinate  

**Value type:** `globecoordinate`

## Monolingual text (monolingual text)

Literal data field for a string that is not translated into other languages. Defined once and reused across all languages. Typical uses include geographical names in the local language, identifiers, chemical formulas, or Latin scientific names.

- **language** – explicit value identifying the language of the text  
- **value** – explicit value for the language-specific string  

**Value type:** `monolingualtext`

## Quantity (quantity)

Literal data field for a quantity associated with a well-defined unit. The unit is part of the entered value.

- **amount** – implicit numeric part of the value  
- **unit** – implicit unit part (defaults to “1”)  
- **upperbound** – upper bound of the quantity  
- **lowerbound** – lower bound of the quantity  

**Value type:** `quantity`

## String (string)

Literal data field for a string of glyphs. Typically used for identifiers whose written form does not depend on the reader’s language.

- **value** – explicit value for the string  

**Value type:** `string`

## Time (time)

Literal data field for a point in time, given with precision and boundaries. Internally stored using the specified calendar model.

- **time** – explicit timestamp resembling ISO 8601 (e.g. `+2013-01-01T00:00:00Z`)  
- **timezone** – signed integer offset from UTC in minutes  
- **before** – integer for how many units after the given time it could be  
- **after** – integer for how many units before the given time it could be  
- **precision** – short integer indicating precision  
  - 0: billion years  
  - 1: hundred million years  
  - …  
  - 6: millennium  
  - 7: century  
  - 8: decade  
  - 9: year  
  - 10: month  
  - 11: day  
  - 12: hour  
  - 13: minute  
  - 14: second  
- **calendarmodel** – explicit value identifying the calendar model  

**Value type:** `time`

## Musical notation (string)

Literal data field for a musical score written in LilyPond notation.

**Value type:** `string`

## Mathematical expression (string)

Literal data field for mathematical expressions, formulas, and equations expressed in a variant of LaTeX.

**Value type:** `string`

## Entity Schema (Wikibase entity id)

Link to Entity Schemas stored in the configured namespace in the same wiki. The value must be given without the namespace prefix.

**Value type:** `wikibase-entityid`

## Lexeme (Wikibase entity id)

Link to lexemes on the project. When a value is entered, the project’s “Lexeme” namespace will be searched for matching lexemes.

**Value type:** `wikibase-entityid`

## Form (Wikibase entity id)

Link to forms on the project. When a value is entered, the project’s “Lexeme” namespace will be searched for matching forms.

**Value type:** `wikibase-entityid`

## Sense (Wikibase entity id)

Link to senses on the project. When a value is entered, the project’s “Lexeme” namespace will be searched for matching senses.

**Value type:** `wikibase-entityid`
