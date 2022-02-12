import os
import json

def get_story():
    '''story.jsonを順番に取得する関数'''
    here = os.path.dirname(__file__)
    story_file = os.path.join(here,"story.json")
    index_file = os.path.join(here,"story_index.json")

    with open(story_file,"r",encoding="utf-8") as f:
        story = json.load(f)
    
    with open(index_file,"r") as f:
        index = json.load(f)
    
    idx = index["index"]
    storyline = story[idx]["msg"]

    #次回ツイート用にindex更新。最後まで来たら最初に戻る。
    next_idx = idx + 1
    if len(story) == next_idx:
        next_idx = 0
    
    with open(index_file,"w") as f:
        json.dump({"index":next_idx},f)

    return storyline

if __name__ == "__main__":
    print(get_story())