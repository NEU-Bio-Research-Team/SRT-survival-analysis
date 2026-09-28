# C07 — hiệu năng phân tầng (không fit mới)

Prediction test đã lưu của Đợt 2 (@S4, gộp F1–F3), chấm riêng theo tầng. Với L, G của IPCW được ước lượng lại trong từng tầng. Tầng: spell đầu tiên vs tái gia nhập; known-start vs unknown-start.

| model | tầng | n | điểm | điểm ref (cùng tầng) | skill |
|---|---|---:|---:|---:|---:|
| D00 AgeOnly | first spell | 22,929 | 0.06943 | | |
| D00 AgeOnly | recurrent | 13,125 | 0.10604 | | |
| D00 AgeOnly | known-start | 28,122 | 0.10332 | | |
| D00 AgeOnly | unknown-start | 7,932 | 0.00986 | | |
| D01 Cloglog | first spell | 22,929 | 0.06307 | | |
| D01 Cloglog | recurrent | 13,125 | 0.09459 | | |
| D01 Cloglog | known-start | 28,122 | 0.09297 | | |
| D01 Cloglog | unknown-start | 7,932 | 0.00922 | | |
| D04 FlexCloglog | first spell | 22,929 | 0.06300 | | |
| D04 FlexCloglog | recurrent | 13,125 | 0.09395 | | |
| D04 FlexCloglog | known-start | 28,122 | 0.09259 | | |
| D04 FlexCloglog | unknown-start | 7,932 | 0.00928 | | |
| D05 BoostedHazard | first spell | 22,929 | 0.06299 | | |
| D05 BoostedHazard | recurrent | 13,125 | 0.09417 | | |
| D05 BoostedHazard | known-start | 28,122 | 0.09267 | | |
| D05 BoostedHazard | unknown-start | 7,932 | 0.00935 | | |
| D06 MLPHazard | first spell | 22,929 | 0.06289 | | |
| D06 MLPHazard | recurrent | 13,125 | 0.09372 | | |
| D06 MLPHazard | known-start | 28,122 | 0.09234 | | |
| D06 MLPHazard | unknown-start | 7,932 | 0.00948 | | |
| L00 KM | first spell | 22,929 | 0.12082 | | |
| L00 KM | recurrent | 13,125 | 0.14832 | | |
| L00 KM | known-start | 28,122 | 0.15313 | | |
| L00 KM | unknown-start | 7,932 | 0.05172 | | |
| L02 CoxNet | first spell | 22,929 | 0.08065 | | |
| L02 CoxNet | recurrent | 13,125 | 0.12098 | | |
| L02 CoxNet | known-start | 28,122 | 0.11779 | | |
| L02 CoxNet | unknown-start | 7,932 | 0.01565 | | |
| L07 DeepSurv | first spell | 22,929 | 0.07870 | | |
| L07 DeepSurv | recurrent | 13,125 | 0.11967 | | |
| L07 DeepSurv | known-start | 28,122 | 0.11565 | | |
| L07 DeepSurv | unknown-start | 7,932 | 0.01543 | | |
| L08 CoxTime | first spell | 22,929 | 0.08002 | | |
| L08 CoxTime | recurrent | 13,125 | 0.11998 | | |
| L08 CoxTime | known-start | 28,122 | 0.11682 | | |
| L08 CoxTime | unknown-start | 7,932 | 0.01562 | | |
| L09 DeepHitSingle | first spell | 22,929 | 0.07719 | | |
| L09 DeepHitSingle | recurrent | 13,125 | 0.11858 | | |
| L09 DeepHitSingle | known-start | 28,122 | 0.11388 | | |
| L09 DeepHitSingle | unknown-start | 7,932 | 0.01549 | | |
| L05 RSF | first spell | 22,929 | 0.07742 | | |
| L05 RSF | recurrent | 13,125 | 0.11924 | | |
| L05 RSF | known-start | 28,122 | 0.11440 | | |
| L05 RSF | unknown-start | 7,932 | 0.01542 | | |
