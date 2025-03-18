from datetime import datetime
import json
import pendulum
from retrying import retry
import requests
from notion_helper import NotionHelper
import utils
from dotenv import load_dotenv

load_dotenv()

from config import (
    plants_properties_type_dict,
    TAG_ICON_URL,
    USER_ICON_URL,
)
from utils import get_icon




FOREST_URL_HEAD = "https://forest-china.upwardsware.com"
FOREST_APP_VERSION = "4.86.2"
FOREST_LOGIN_URL = FOREST_URL_HEAD + "/api/v1/sessions"
FOREST_CLAENDAR_URL = (
    FOREST_URL_HEAD
    + "/api/v1/plants?from_date=1970-01-01T00:00:00.000Z&seekruid={user_id}"
)
FOREST_PLANTS_URL = (
    FOREST_URL_HEAD
    + "/api/v1/products/coin_tree_types?seekrua=android_cn-"
    + FOREST_APP_VERSION
    + "&seekruid={user_id}"
)
TODO = "97955f34653b4658bc0aaa50423be45f"
FOREST_TAG_URL = FOREST_URL_HEAD + "/api/v1/tags?seekruid={id}"
email = "linkang.ma@gmail.com"
password = "FFitness06"
headers = {"Content-Type": "application/json"}
s = requests.Session()
auth = ("2ef95512ce5b1528809f9a03a68e02b1", "api_token")


def get_tags(session,user_id):
    dict = {}
    r = session.get(FOREST_TAG_URL.format(id=user_id), headers=headers)
    tags = r.json().get("tags")
    with open('tags.json', 'w', encoding='utf-8') as f:
        json.dump(r.json(), f, ensure_ascii=False, indent=4)
    for tag in tags:
        id = tag.get("tag_id")
        name = tag.get("title")
        delete = tag.get("deleted")
        # if not delete:
        dict[id] = name
    return dict


def get_plants_type(session,user_id):
    """
    获取所有的植物类型
    """
    r = session.get(FOREST_PLANTS_URL.format(user_id=user_id), headers=headers)
    # r = session.get(FOREST_PLANTS_URL.format(user_id=user_id), headers=headers)
    # r = session.get("https://forest-china.upwardsware.com/api/v1/users/462422/coin?seekrua=android_cn-4.86.2&seekruid=462422", headers=headers)
    # r = session.get("https://forest-china.upwardsware.com/api/v1/gem_rewards?seekrua=android_cn-4.86.2&seekruid=462422", headers=headers)
    # r = session.get("https://forest-china.upwardsware.com/api/v1/boosts?seekrua=android_cn-4.86.2&seekruid=462422", headers=headers)
    # r = session.get("https://forest-china.upwardsware.com/api/v1/users/462422?seekrua=android_cn-4.86.2&seekruid=462422", headers=headers)
    # r = session.get("https://forest-china.upwardsware.com/api/v1/tree_types/unlocked_timestamps?seekrua=android_cn-4.86.2&seekruid=462422", headers=headers)
    # r = session.get("https://forest-china.upwardsware.com/api/v1/achievements?today=2025-03-10T16%3A00%3A00.000Z&achievement_system_2020=true&seekrua=android_cn-4.86.2&seekruid=462422", headers=headers)
    # r = session.get("https://forest-china.upwardsware.com/api/v1/timelines?start_date=1970-01-01T00%3A00%3A00.000Z&end_date=2025-03-11T11%3A23%3A35.965Z&seekrua=android_cn-4.86.2&seekruid=462422", headers=headers)
    products = r.json()["all_products"]
    return {x.get("id"): x for x in products}


def get_plants(session,user_id):
    r = session.get(FOREST_CLAENDAR_URL.format(user_id=user_id), headers=headers)
    plants = r.json()
    plants.sort(key=lambda plant: plant.get("start_time"))
    for plant in plants:
        item = {}
        item["id"] = str(plant.get("id"))
        tag = forest_tag_dict[plant.get("tag")]
        emoji,tag=utils.split_emoji_from_string(tag)
        item["标题"]= tag
        item["分类"] = [
            notion_helper.get_relation_id(
                tag,
                notion_helper.category_database_id,
                {"type": "emoji", "emoji": emoji},
                properties={"id": {"number": plant.get("tag")}},
            )
        ]
        tree_relation_ids = []
        for tree in plant.get("trees"):
            t = forest_tree_dict.get(tree.get("tree_type"))
            if t :
                tree_relation_ids.append(notion_helper.get_relation_id(t.get("title"),notion_helper.tree_database_id,icon=get_icon(t.get("icon_url")),properties={"id": {"number": tree.get("tree_type")}}))
        if tree_relation_ids:
            item["树"] = tree_relation_ids
        start_time = pendulum.parse(plant.get("start_time"), tz='UTC')
        end_time = pendulum.parse(plant.get("end_time"), tz='UTC').int_timestamp
        if start_time.replace(second=0).int_timestamp <= lastest:
            continue;
        item["开始时间"] = start_time.int_timestamp
        item["结束时间"] = end_time
        note = plant.get("note")
        if note:
            item["标题"] = note.strip()
        properties = utils.get_properties(item, plants_properties_type_dict)
        notion_helper.get_date_relation(properties, start_time)
        parent = {
            "database_id": notion_helper.plant_database_id,
            "type": "database_id",
        }
        notion_helper.create_page(
            parent=parent, properties=properties, icon={"type": "emoji", "emoji": emoji}
        )


def login(session,username,password):
    data = {"session": {"email": username, "password": password}}
    r = session.post(FOREST_LOGIN_URL, headers=headers, json=data)
    user_id = r.json().get("user_id")
    return user_id

def get_lastest():
    filter = {"property": "id", "rich_text": {"is_not_empty": True}}
    sorts=[{"property": "开始时间", "direction": "descending"}]
    result = notion_helper.query(
        database_id=notion_helper.plant_database_id,
        page_size=1,
        sorts=sorts,
        filter=filter
    )
    results = result.get("results")
    if results:
        return utils.get_property_value(results[0].get("properties").get("开始时间"))
    else:
        return 0


if __name__ == "__main__":
    notion_helper = NotionHelper()
    config = notion_helper.config
    username = config.get("Forest账号")
    password = config.get("Forest密码")
    session = requests.Session()
    lastest = get_lastest()
    user_id = login(session,username,password)
    forest_tag_dict = get_tags(session,user_id)
    forest_tree_dict = get_plants_type(session,user_id)
    get_plants(session,user_id)
