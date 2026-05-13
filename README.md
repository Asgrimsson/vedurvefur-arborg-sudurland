# Veðurvefur Árborgar og Suðurlands

Staðbundinn veðurvefur með skóla-, ferðalaga- og fræðslusniði.

## Hvað er inni?

- Núverandi veður fyrir Árborg og Suðurland
- 48 klst. spá með línuritum
- Dagaspá
- Útikennslumælir fyrir kennara
- Ferðaveður á leiðum eins og Selfoss → Reykjavík
- Kort af stöðum
- Fræðsluhluti um veður, loftslag og jökla
- Tenglar í Veðurstofu Íslands, Umferðina og Vegagerðina

## Uppsetning á tölvu

1. Opnaðu möppuna í VS Code eða CMD.
2. Settu upp pakka:

```bash
pip install -r requirements.txt
```

3. Afritaðu `.env.example` og breyttu heitinu í `.env`.
4. Settu API lykilinn þinn inn:

```env
OPENWEATHER_API_KEY=þinn_lykill_hér
```

5. Keyrðu vefinn:

```bash
streamlit run app.py
```

## Render / Streamlit Cloud

Ekki setja API lykilinn inn í kóðann.

Settu hann sem environment variable eða secret:

```text
OPENWEATHER_API_KEY
```

## Athugasemd um One Call 3.0

Appið reynir fyrst að nota OpenWeather One Call 3.0. Ef lykillinn hefur ekki virka One Call áskrift reynir appið sjálfkrafa fallback í OpenWeather 2.5 current/forecast, svo þú getur samt prófað vefinn.

## Næstu skref

- Tengja opinberar íslenskar viðvaranir betur frá Veðurstofu Íslands
- Tengja gagnaveitu Vegagerðarinnar fyrir færð og myndavélar
- Bæta við íslenskum veðurmetum úr traustum heimildum
- Gera Google Sites embed útgáfu