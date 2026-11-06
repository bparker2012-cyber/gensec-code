# Homework template execution contract

Reference: retained `homework-template.docx` in this directory, SHA-256
58aca05c972a46821ba8b9d20afb3bb83abcddf90dbee4a49a1abbef6c6df72e.
It renders to two pages. The reference remains byte-for-byte unchanged.
Baseline package inventory is `template-inventory.json`; visual evidence is
`../qa/template/page-1.png` and `page-2.png`. Style evidence is retained in
`../qa/template-styles.json`.

One portrait A4 section, 8.2681 by 11.6931 inches. Margins: left/right/top
0.7875 inches, bottom 1.1757 inches. Preserve section settings and the existing
footer page field. Title uses the source Title style (28 pt); subtitle uses
Subtitle (18 pt). Metadata labels use source 14 pt bold Liberation Sans,
values 12 pt. Body instructions use the source serif body text and Roman and
lettered list definitions. Preserve all instruction paragraphs, highlights,
numbering, and title formatting. No reference tables or images are present.

Slots are zero-based direct body paragraph indexes in word/document.xml:
2 homework number; 5 student name; 7 FAU email; 18 recording URL or honest
pending status; 20 repository URL; 22 application name; 24 description under
half a page; 27 development heading; 28 first task introduction. Retain run
properties when filling these slots. Leave all other source text untouched.

Append task prompts as ordinary readable body text, followed by the actual
VS Code screenshots and generated-code evidence. New paragraphs reuse the
source Body Text role; headings reuse the source bold metadata type scale.
Evidence pages may begin with explicit page breaks for readability. Keep the
same portrait geometry and the source footer throughout. Screenshots are
embedded unaltered, each at the full available text width, with a short
caption. Retain high-resolution originals in Git.

Preserve all original package parts byte-for-byte except document.xml,
document.xml.rels, and Content_Types.xml. Only add media parts used by the
appended evidence. Do not rewrite styles, numbering, theme, opaque parts,
footer, or existing relationships. New image relationships are additive.

Required checks: package preservation comparison; unchanged source checksum;
same section geometry; all slots filled or honestly pending; every final page
rendered and inspected; all prompt text and screenshots legible. The recording
URL remains pending until a real student recording is supplied. Do not claim
live AI regeneration or Canvas submission from the clean clone test alone.

Source blank spacer paragraphs 25 and 26 may be removed to prevent an empty
page after the metadata. This intentional whitespace change does not alter
any source instruction, style, list definition, or page geometry.
