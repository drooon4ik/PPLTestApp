import json, time, argostranslate.translate as T

api = json.load(open('api_data.json', encoding='utf-8'))
CACHE = 'expl_translations.json'
import os
res = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

qids = list(api.keys())
total = len(qids)
start = time.time(); last = 0
for i, qid in enumerate(qids):
    if qid in res and res[qid].get('en') and res[qid].get('ru'):
        continue
    pl = api[qid].get('explanation_pl', '')
    if not pl.strip():
        res[qid] = {"en": "", "ru": ""}
    else:
        en = T.translate(pl, 'pl', 'en')
        ru = T.translate(en, 'en', 'ru')
        res[qid] = {"en": en, "ru": ru}
    if time.time()-last >= 3:
        done = i+1; el = time.time()-start; rate = done/el if el else 0
        eta = (total-done)/rate/60 if rate else 0
        print(f"[EXPL] Переведено пояснений: {done}/{total} ({100*done//total}%) | осталось ~{eta:.1f} мин", flush=True)
        last = time.time()
        json.dump(res, open(CACHE,'w'), ensure_ascii=False)

json.dump(res, open(CACHE,'w'), ensure_ascii=False)
print(f"[EXPL] ГОТОВО. Всего: {len(res)}", flush=True)
