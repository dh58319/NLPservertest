import pickle  
import word2vec
from process_similar import get_nearest
from datetime import date, datetime
from pytz import utc, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, AnyStr

NUM_SECRETS = 9936
KST = timezone('Asia/Seoul')
FIRST_DAY = date(2023, 3, 20)


app = FastAPI()

scheduler = BackgroundScheduler()
scheduler.start()


print("loading valid nearest")
with open('data/valid_nearest.dat', 'rb') as f:
    valid_nearest_words, valid_nearest_vecs = pickle.load(f)
with open('data/secrets.txt', 'r', encoding='utf-8') as f:
    secrets = [l.strip() for l in f.readlines()]
print("initializing nearest words for solutions")
app.secrets = dict()
app.nearests = dict()
current_puzzle = (utc.localize(datetime.utcnow()).astimezone(KST).date() - FIRST_DAY).days % NUM_SECRETS
for offset in range(-2, 2):
    puzzle_number = (current_puzzle + offset) % NUM_SECRETS
    # print("current puzzle number",puzzle_number)
    secret_word = secrets[puzzle_number]
    # print("secret word",secret_word)
    app.secrets[puzzle_number] = secret_word
    app.nearests[puzzle_number] = get_nearest(puzzle_number, secret_word, valid_nearest_words, valid_nearest_vecs)
    #print(app.nearests[puzzle_number])
    
@scheduler.scheduled_job(trigger=CronTrigger(hour=1, minute=0, timezone=KST))
def update_nearest():
    print("scheduled stuff triggered!")
    next_puzzle = ((utc.localize(datetime.utcnow()).astimezone(KST).date() - FIRST_DAY).days + 1) % NUM_SECRETS
    next_word = secrets[next_puzzle]
    to_delete = (next_puzzle - 4) % NUM_SECRETS
    if to_delete in app.secrets:
        del app.secrets[to_delete]
    if to_delete in app.nearests:
        del app.nearests[to_delete]
    app.secrets[next_puzzle] = next_word
    app.nearests[next_puzzle] = get_nearest(next_puzzle, next_word, valid_nearest_words, valid_nearest_vecs)
    

@app.get("/")
def main():
    return {"message": "Hello World"}

@app.get("/api/komantle")
def get_similarities() -> Dict[str, int]:
    current_puzzle = (utc.localize(datetime.utcnow()).astimezone(KST).date() - FIRST_DAY).days % NUM_SECRETS
    secret_word = app.secrets.get(current_puzzle)
    if secret_word is None:
        raise HTTPException(status_code=404, detail="Secret word not found")
    nearest_words = app.nearests.get(current_puzzle)
    if nearest_words is None:
        raise HTTPException(status_code=404, detail="Nearest words not found")
    result = {
        "keyword": secret_word,
        "relativeItems": {}
    }
    
    #print (type(nearest_words))
    #print (nearest_words)
    #print (nearest_words.values())
    # for word in nearest_words:
    #     print(word = word, similarity = similarity)
    #     result["relativeItems"][word] = similarity
    for word in nearest_words:
        #print(word)
        print(nearest_words[word][0])
        result["relativeItems"][word] = round(nearest_words[word][1]*100,3)
    return JSONResponse(content=result)

