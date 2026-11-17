# Первичные источники проверки T044

Локальные SHA-256 — в `source_checks.json`. Полные загруженные документы находятся в исключённом из Git `source_downloads/`; публикация этих копий не производилась. Собственная отрисовка таблиц сохраняет значения и порядок строк, но не исходную пагинацию и объединения ячеек DOCX.

| Источник | Проверенное место / способ |
|---|---|
| [S2, DOI 10.1021/acsomega.8b02319](https://doi.org/10.1021/acsomega.8b02319) | Переданный `data/raw/html/S2.xml`: Tables 1–2, §§2.1, 2.2, 2.4, 4.1–4.6. Исходное изображение формулы `ao-2018-02319p_m001.jpg` просмотрено в существующем локальном кэше первоисточников; его публичный пакет: [Europe PMC supplementaryFiles](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6648867/supplementaryFiles). |
| [S100 Supporting Information](https://pstorage-acs-6854636.s3.amazonaws.com/3743113/ie5b03517_si_001.pdf) | Повторно скачан публичный файл, PDF-страница 7 отрисована и просмотрена (`rendered/S100_page7.png`); разделы S1–S4 прочитаны по переданному тексту. Новые координаты с картинки не измерялись. |
| [SRC-03](https://doi.org/10.1016/j.cej.2023.145349) | Переданный `si_S1385894723040809_mmc1.docx`, Table S2 и §S4; значения и структура ячеек прочитаны непосредственно из DOCX XML. Основная статья не объявляется прочитанной. |
| [SRC-06](https://doi.org/10.1016/j.apcatb.2026.127731) | Переданный `si_S0926337326013524_mmc1.docx`, Tables S1–S3, Table 4, §§1.1, 1.3–1.4; проверена [карточка Macquarie](https://researchers.mq.edu.au/en/publications/enhanced-dual-pathway-photocatalytic-hydrogen-peroxide-production/). |
| [HP20, DOI 10.1038/s41467-025-57972-7](https://doi.org/10.1038/s41467-025-57972-7) | [Официальный JATS](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11911411/fullTextXML), `source_downloads/HP20.xml`: preparation, sorption, mechanism, synthesis Eq.1, activation. |
| [Потолок, DOI 10.1021/acsomega.4c07631](https://doi.org/10.1021/acsomega.4c07631) | [Официальный JATS](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11683601/fullTextXML), `source_downloads/stoichiometry.xml`: §2.5/Fig.3. |
| [Третичные амины, Foo et al.](https://chemistry-europe.onlinelibrary.wiley.com/doi/10.1002/cssc.201600809) | Открытая аннотация, прочитана через web; основной платный текст не запрашивался. |

Сетевые обращения 17.11.2026: web-PMC → CAPTCHA, DOI ACS → 403, web-EBI → tool error; без обхода. Wiley/Macquarie открылись. Обычный curl к официальному EBI API и публичному ACS SI → exit 0. Python urllib в этой среде вернул CERTIFICATE_VERIFY_FAILED; в curl проверка TLS оставалась включённой.

Повторное получение трёх файлов для `source_checks.py` (из корня репозитория):

```sh
mkdir -p reviews/T044_checks/source_downloads
curl --fail --location --max-time 30 https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11911411/fullTextXML --output reviews/T044_checks/source_downloads/HP20.xml
curl --fail --location --max-time 30 https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11683601/fullTextXML --output reviews/T044_checks/source_downloads/stoichiometry.xml
curl --fail --location --max-time 30 https://pstorage-acs-6854636.s3.amazonaws.com/3743113/ie5b03517_si_001.pdf --output reviews/T044_checks/source_downloads/S100_SI.pdf
```

Прямая конвертация исходных DOCX через установленный LibreOffice завершилась exit 1 (`Unspecified Application Error`, предупреждения Fontconfig). Вместо неё сделана явно помеченная отрисовка извлечённых исходных таблиц; это ограничение полноты визуальной проверки отмечено в ревью. S2 формула и S100 PDF просмотрены в оригинальном изображении. Журнал полной агентской сессии не создавался.
