import os
import time
import logging
import threading
import requests
import webbrowser
from collections import defaultdict
from PIL import Image, ImageTk
import cv2
import tkinter as tk
from tkinter import ttk, scrolledtext

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants
GRAPHQL_URL = "https://api.defikingdoms.com/graphql"
PRICE_MULTIPLIER = 10**18


def read_addresses_from_file(file_path):
    addresses = []
    try:
        with open(file_path, "r") as file:
            for line in file:
                line = line.split("#", 1)[0].strip()
                if line:
                    addresses.append(line)
    except FileNotFoundError:
        logging.error(f"Address file {file_path} not found.")
    return addresses


class SearchLogic:
    """
    Encapsulates the logic for searching, filtering, and grouping heroes.
    Provides methods for parsing user input, applying filters, and finding
    summoning pairs based on various criteria.
    """

    def parse_class_input(self, user_input):
        user_input = ", ".join(str(item) for item in user_input)
        if user_input.strip().lower() == "none":
            return None
        main_classes = []
        input_parts = user_input.replace(" ", "").split(",")
        for part in input_parts:
            if "-" in part:
                start, end = part.split("-")
                main_classes.extend(range(int(start), int(end) + 1))
            elif part.startswith("[") and part.endswith("]"):
                class_list = part[1:-1].split(";")
                main_classes.extend([int(cls) for cls in class_list])
            else:
                main_classes.append(int(part))
        return main_classes

    def group_heroes_by_criteria(self, heroes, criteria):
        groups = defaultdict(list)
        for hero in heroes:
            key = str(hero[criteria])
            groups[key].append(hero)
        return groups

    def is_pair_already_considered(self, pair, considered_pairs):
        return pair in considered_pairs or tuple(reversed(pair)) in considered_pairs

    def apply_filters(self, hero1, hero2, filters, considered_pairs):
        pair = (hero1["id"], hero2["id"])
        if self.is_pair_already_considered(pair, considered_pairs):
            return False
        if (
            filters.get("heroId")
            and filters.get("heroId") != hero1["id"]
            and filters.get("heroId") != hero2["id"]
        ):
            return False
        if filters.get("cooldown"):
            if (
                hero1.get("nextSummonTime") >= time.time()
                or hero2.get("nextSummonTime") >= time.time()
            ):
                return False
        if filters.get("level"):
            if hero1.get("level") != hero2.get("level"):
                return False
        if filters.get("rarity"):
            if hero1.get("rarity") != hero2.get("rarity"):
                return False
        if filters.get("generation"):
            if hero1.get("generation") != hero2.get("generation"):
                return False
        if "assistingPrice" in hero1 and "assistingPrice" in hero2:
            return False
        if filters.get("mainClass"):
            if not (
                (
                    hero1["mainClass"] % 2 == 0
                    and hero1["mainClass"] + 1 == hero2["mainClass"]
                )
                or (
                    hero2["mainClass"] % 2 == 0
                    and hero2["mainClass"] + 1 == hero1["mainClass"]
                )
            ):
                return False
        if filters.get("subClass"):
            if not (
                (
                    hero1["subClass"] % 2 == 0
                    and hero1["subClass"] + 1 == hero2["subClass"]
                )
                or (
                    hero2["subClass"] % 2 == 0
                    and hero2["subClass"] + 1 == hero1["subClass"]
                )
            ):
                return False
        if filters.get("summons"):
            if hero1["summonsRemaining"] != hero2["summonsRemaining"]:
                return False
        if "ability" in filters:
            ability_type = filters["ability"]["type"]
            required_matches = filters["ability"]["matches_required"]
            matches = self.count_ability_matches(hero1, hero2, ability_type)
            if matches < required_matches:
                return False

        considered_pairs.add(pair)
        return True

    def count_total_matches(self, hero1, hero2):
        match_count = 0
        if (
            hero1["mainClass"] % 2 == 0 and hero1["mainClass"] + 1 == hero2["mainClass"]
        ) or (
            hero2["mainClass"] % 2 == 0 and hero2["mainClass"] + 1 == hero1["mainClass"]
        ):
            match_count += 1
        if (
            hero1["subClass"] % 2 == 0 and hero1["subClass"] + 1 == hero2["subClass"]
        ) or (
            hero2["subClass"] % 2 == 0 and hero2["subClass"] + 1 == hero1["subClass"]
        ):
            match_count += 1
        match_count += self.count_all_ability_matches(hero1, hero2)
        return match_count

    def get_ability_pairs(self, ability_type):
        if ability_type == "basic":
            return [(0, 1), (2, 3), (4, 5), (6, 7)]
        elif ability_type == "advanced":
            return [(16, 17), (18, 19)]
        elif ability_type == "elite":
            return [(24, 25)]
        return []

    def count_all_ability_matches(self, hero1, hero2):
        ability_pairs = [(0, 1), (2, 3), (4, 5), (6, 7), (16, 17), (18, 19), (24, 25)]
        matches = 0
        for a1, a2 in ability_pairs:
            if (hero1["active1"] == a1 and hero2["active1"] == a2) or (
                hero1["active1"] == a2 and hero2["active1"] == a1
            ):
                matches += 1
            if (hero1["active2"] == a1 and hero2["active2"] == a2) or (
                hero1["active2"] == a2 and hero2["active2"] == a1
            ):
                matches += 1
            if (hero1["passive1"] == a1 and hero2["passive1"] == a2) or (
                hero1["passive1"] == a2 and hero2["passive1"] == a1
            ):
                matches += 1
            if (hero1["passive2"] == a1 and hero2["passive2"] == a2) or (
                hero1["passive2"] == a2 and hero2["passive2"] == a1
            ):
                matches += 1

        return matches

    def count_ability_matches(self, hero1, hero2, ability_type):
        matches = 0
        ability_pairs = []
        if ability_type == "basic":
            ability_pairs = [(0, 1), (2, 3), (4, 5), (6, 7)]
        elif ability_type == "advanced":
            ability_pairs = [(16, 17), (18, 19)]
        elif ability_type == "elite":
            ability_pairs = [(24, 25)]

        for a1, a2 in ability_pairs:
            if (hero1["active1"] == a1 and hero2["active1"] == a2) or (
                hero1["active1"] == a2 and hero2["active1"] == a1
            ):
                matches += 1
            if (hero1["active2"] == a1 and hero2["active2"] == a2) or (
                hero1["active2"] == a2 and hero2["active2"] == a1
            ):
                matches += 1
            if (hero1["passive1"] == a1 and hero2["passive1"] == a2) or (
                hero1["passive1"] == a2 and hero2["passive1"] == a1
            ):
                matches += 1
            if (hero1["passive2"] == a1 and hero2["passive2"] == a2) or (
                hero1["passive2"] == a2 and hero2["passive2"] == a1
            ):
                matches += 1

        return matches

    def find_summoning_pairs(self, grouped_heroes, filters):
        pairs = []
        considered_pairs = set()

        all_heroes = [hero for heroes in grouped_heroes.values() for hero in heroes]

        for i, hero1 in enumerate(all_heroes):
            for hero2 in all_heroes[i + 1 :]:
                pair = (hero1["id"], hero2["id"])
                if self.is_pair_already_considered(pair, considered_pairs):
                    continue

                if self.apply_filters(hero1, hero2, filters, considered_pairs):
                    match_count = self.count_total_matches(hero1, hero2)
                    pairs.append((hero1["id"], hero2["id"], match_count))
                    considered_pairs.add(pair)

        return pairs

    def search_heroes(
        self,
        text_widget,
        main_class,
        sub_class,
        min_summon,
        max_summon,
        min_gen,
        max_gen,
        min_rarity,
        max_rarity,
        min_level,
        max_level,
        match_level,
        match_rarity,
        match_summon,
        match_gen,
        match_mainclass,
        match_subclass,
        match_sale,
        ignore_cooldown,
        sale_limit,
        match_hire,
        hire_limit,
        ability_type,
        ability_matches,
        hero_id,
        *args,
    ):
        """Search for heroes based on specified criteria and filters."""

        filters = {}
        main_classes = self.parse_class_input(main_class)
        main_classes = None if len(main_class) == 0 else main_classes

        sub_classes = self.parse_class_input(sub_class)
        sub_classes = None if len(sub_class) == 0 else sub_classes

        match_var = hero_id.get().strip()
        match_id = bool(match_var)
        hero_id_value = str(hero_id.get().strip()) if hero_id.get().strip() else None
        if match_id == True:
            filters["heroId"] = hero_id_value
        filters["generation"] = match_gen == True
        filters["cooldown"] = ignore_cooldown == False
        filters["level"] = match_level == True
        filters["rarity"] = match_rarity == True
        filters["summons"] = match_summon == True
        filters["mainClass"] = match_mainclass == True
        filters["subClass"] = match_subclass == True

        ability_ranges = {
            "basic": range(0, 8),
            "advanced": range(16, 20),
            "elite": range(24, 26),
        }

        ability_queries = [
            {"type": "passive1", "filter": "passive1_in"},
            {"type": "passive2", "filter": "passive2_in"},
            {"type": "active1", "filter": "active1_in"},
            {"type": "active2", "filter": "active2_in"},
        ]

        if ability_type in ["basic", "advanced", "elite"]:
            filters["ability"] = {
                "type": ability_type,
                "matches_required": ability_matches,
            }

        all_heroes = []

        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, "Searching for heroes...\n")
        if match_id:
            GraphQLQuery.single_hero_query(hero_id_value, all_heroes)

        text_widget.insert(tk.END, "Finding all heroes in wallets...\n")

        variables = {"account_address": address_list}
        variables["main_classes"] = main_classes
        variables["sub_classes"] = sub_classes
        variables["min_summon"] = min_summon
        variables["max_summon"] = max_summon
        variables["max_generation"] = int(max_gen)
        variables["min_generation"] = int(min_gen)
        variables["max_rarity"] = max_rarity
        variables["min_rarity"] = min_rarity
        variables["max_level"] = max_level
        variables["min_level"] = min_level
        if ability_type in ["advanced", "elite"]:
            selected_ability_range = list(ability_ranges.get(ability_type, []))
            variables["ability_list"] = selected_ability_range

        GraphQLQuery.wallet_hero_query(
            variables, ability_queries, text_widget, all_heroes
        )

        if match_sale == True:
            filters["tavern"] = True
            price_limit = int(sale_limit) * PRICE_MULTIPLIER
            variables["price_limit"] = str(price_limit)
            GraphQLQuery.tavern_sale_query(
                variables, ability_queries, text_widget, all_heroes
            )

        if match_hire == True:
            max_hiring_price = int(hire_limit) * PRICE_MULTIPLIER
            variables["price_limit"] = str(max_hiring_price)

            GraphQLQuery.tavern_hire_query(
                variables, ability_queries, text_widget, all_heroes
            )

        text_widget.insert(tk.END, f"Total heroes found: {len(all_heroes)}\n")
        time.sleep(1)

        grouped_heroes = self.group_heroes_by_criteria(all_heroes, "mainClass")
        text_widget.insert(tk.END, f"Evaluating summoning pairs...\n")
        matching_pairs = self.find_summoning_pairs(grouped_heroes, filters)
        matching_pairs.sort(key=lambda pair: pair[2], reverse=True)

        return all_heroes, matching_pairs


class VideoPlayer(tk.Label):
    """
    A custom Tkinter Label widget for playing videos using OpenCV.
    Plays a video in a Tkinter application and handles video end events.
    """

    def __init__(self, master, video_path, on_video_end_callback, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.video_path = video_path
        self.on_video_end_callback = on_video_end_callback
        if os.path.exists(video_path):
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                logging.error(f"Failed to open video: {video_path}")
                self.cap = None
        else:
            logging.error(f"Video file not found: {video_path}")
            self.cap = None
        self.playing = False
        self.image = None
        self.width = 360
        self.height = 360

        blank_image = Image.new("RGB", (self.width, self.height), color="black")
        self.blank_image_tk = ImageTk.PhotoImage(blank_image)
        self.config(image=self.blank_image_tk)

    def start(self):
        if self.cap is not None:
            self.pack(expand=True)
            self.playing = True
            self._play()
        else:
            logging.error("Video capture not initialized. Skipping video playback.")

    def stop(self):
        self.playing = False
        self.cap.release()
        self.on_video_end_callback()

    def _play(self):
        if not self.playing:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.stop()
            return
        frame = cv2.resize(frame, (self.width, self.height))
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        self.image = ImageTk.PhotoImage(image)
        self.config(image=self.image)
        self.after(33, self._play)


class GraphQLQuery:
    """
    Provides methods to perform GraphQL queries related to heroes.

    Methods:
        single_hero_query: Queries for a single hero by ID.
        wallet_hero_query: Queries for heroes in a specified wallet.
        tavern_sale_query: Queries for heroes available for sale in the tavern.
        tavern_hire_query: Queries for heroes available for hire in the tavern.
    """

    def single_hero_query(hero_id, all_heroes):
        query = """
        query getHero($hero_id: ID!){
            hero(id: $hero_id) {
            id
            mainClass
            subClass
            summonsRemaining
            passive1
            passive2
            active1
            active2
            generation
            statGenes
            rarity
            nextSummonTime
            level
            owner {
                name
            }
            }
        }
        """
        variables = {"hero_id": hero_id}
        result = requests.post(
            GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        current_hero = result.json()
        current_hero = current_hero["data"]["hero"]
        all_heroes.append(current_hero)
        time.sleep(1)
        return all_heroes

    def wallet_hero_query(variables, ability_queries, text_widget, all_heroes):
        if "ability_list" in variables:
            for ability_query in ability_queries:
                set_number = 0
                skip_number = 0
                ability_filter = ability_query["filter"]

                while set_number == 0 or len(current_heroes) == 250:
                    variables["skip_number"] = skip_number
                    query = f"""
                    query getHeroes($account_address: [String!], $skip_number: Int!, $min_summon: Int, $max_summon: Int, $main_classes: [Int], $sub_classes: [Int], $max_generation: Int, $min_generation: Int, $max_rarity: Int, $min_rarity: Int, $max_level: Int, $min_level: Int, $ability_list: [Int]){{
                        heroes(first:250, skip: $skip_number, orderBy: id, orderDirection: desc, where: {{owner_in: $account_address, summonsRemaining_gte: $min_summon, summonsRemaining_lte: $max_summon, mainClass_in: $main_classes, subClass_in: $sub_classes, generation_lte: $max_generation, generation_gte: $min_generation, rarity_lte: $max_rarity, rarity_gte: $min_rarity, level_lte: $max_level, level_gte: $min_level, {ability_filter}: $ability_list}}) {{
                            id
                            mainClass
                            subClass
                            summonsRemaining
                            passive1
                            passive2
                            active1
                            active2
                            generation
                            statGenes
                            rarity
                            nextSummonTime
                            level
                            owner {{
                                name
                            }}
                        }}
                    }}
                    """
                    result = requests.post(
                        GRAPHQL_URL, json={"query": query, "variables": variables}
                    )
                    result_json = result.json()
                    if "data" in result_json and "heroes" in result_json["data"]:
                        current_heroes = result_json["data"]["heroes"]
                        all_heroes.extend(current_heroes)
                        text_widget.insert(
                            tk.END, f"Total heroes in wallets: {len(all_heroes)}\n"
                        )
                    else:
                        text_widget.insert(
                            tk.END, f"Error in query response: {result_json}\n"
                        )
                    time.sleep(1)
                    set_number += 1
                    skip_number = set_number * 250
        else:
            set_number = 0
            skip_number = 0
            while set_number == 0 or len(current_heroes) == 250:
                variables["skip_number"] = skip_number
                query = """
                query getHeroes($account_address: [String!], $skip_number: Int!, $min_summon: Int, $max_summon: Int, $main_classes: [Int], $sub_classes: [Int], $max_generation: Int, $min_generation: Int, $max_rarity: Int, $min_rarity: Int, $max_level: Int, $min_level: Int){
                    heroes(first:250, skip: $skip_number, orderBy: id, orderDirection: desc, where: {owner_in: $account_address, summonsRemaining_gte: $min_summon, summonsRemaining_lte: $max_summon, mainClass_in: $main_classes, subClass_in: $sub_classes, generation_lte: $max_generation, generation_gte: $min_generation, rarity_lte: $max_rarity, rarity_gte: $min_rarity, level_lte: $max_level, level_gte: $min_level}) {
                    id
                    mainClass
                    subClass
                    summonsRemaining
                    passive1
                    passive2
                    active1
                    active2
                    generation
                    statGenes
                    rarity
                    nextSummonTime
                    level
                    owner {
                        name
                    }
                    }
                }
                """
                result = requests.post(
                    GRAPHQL_URL, json={"query": query, "variables": variables}
                )
                current_heroes = result.json()
                current_heroes = current_heroes["data"]["heroes"]
                all_heroes.extend(current_heroes)
                text_widget.insert(
                    tk.END, f"Total heroes in wallets: {len(all_heroes)}\n"
                )
                time.sleep(1)
                set_number += 1
                skip_number = set_number * 250

        return all_heroes

    def tavern_sale_query(variables, ability_queries, text_widget, all_heroes):
        sale_heroes = []
        text_widget.insert(tk.END, "Finding all heroes in tavern for sale...\n")
        if "ability_list" in variables:
            for ability_query in ability_queries:
                set_number = 0
                skip_number = 0
                ability_filter = ability_query["filter"]

                while set_number == 0 or len(current_heroes) == 250:
                    variables["skip_number"] = skip_number
                    query = f"""
                    query saleAuctions($price_limit: String, $skip_number: Int!, $min_summon: Int, $max_summon: Int, $main_classes: [Int], $sub_classes: [Int], $max_generation: Int, $min_generation: Int, $max_rarity: Int, $min_rarity: Int, $max_level: Int, $min_level: Int, $ability_list: [Int]){{
                        heroes(first:250, skip: $skip_number, orderBy: id, orderDirection: desc, where: {{salePrice_not: null, salePrice_lte: $price_limit, summonsRemaining_gte: $min_summon, summonsRemaining_lte: $max_summon, mainClass_in: $main_classes, subClass_in: $sub_classes, generation_lte: $max_generation, generation_gte: $min_generation, rarity_lte: $max_rarity, rarity_gte: $min_rarity, level_lte: $max_level, level_gte: $min_level, {ability_filter}: $ability_list}}) {{
                            id
                            mainClass
                            subClass
                            summonsRemaining
                            passive1
                            passive2
                            active1
                            active2
                            salePrice
                            generation
                            network
                            statGenes
                            rarity
                            nextSummonTime
                            level
                            owner {{
                                name
                            }}
                        }}
                    }}
                    """
                    result = requests.post(
                        GRAPHQL_URL, json={"query": query, "variables": variables}
                    )
                    result_json = result.json()
                    if "data" in result_json and "heroes" in result_json["data"]:
                        current_heroes = result.json()
                        current_heroes = current_heroes["data"]["heroes"]
                        sale_heroes.extend(current_heroes)
                        text_widget.insert(
                            tk.END, f"Total heroes for sale: {len(sale_heroes)}\n"
                        )
                    else:
                        text_widget.insert(
                            tk.END, f"Error in query response: {result_json}\n"
                        )
                    time.sleep(1)
                    set_number += 1
                    skip_number = set_number * 250
        else:
            set_number = 0
            skip_number = 0
            while set_number == 0 or len(current_heroes) == 250:
                variables["skip_number"] = skip_number
                query = """
                query saleAuctions($price_limit: String, $skip_number: Int!, $main_classes: [Int], $sub_classes: [Int], $max_summon: Int, $min_summon: Int, $max_generation: Int, $min_generation: Int, $max_rarity: Int, $min_rarity: Int, $max_level: Int, $min_level: Int){
                    heroes(first: 250, orderBy: id, skip: $skip_number, orderDirection: asc, where: {salePrice_not: null, salePrice_lte: $price_limit, mainClass_in: $main_classes, subClass_in: $sub_classes, summonsRemaining_gte: $min_summon, summonsRemaining_lte: $max_summon, generation_lte: $max_generation, generation_gte: $min_generation, rarity_lte: $max_rarity, rarity_gte: $min_rarity, level_lte: $max_level, level_gte: $min_level}
                    ) {
                        id
                        mainClass
                        subClass
                        summonsRemaining
                        passive1
                        passive2
                        active1
                        active2
                        salePrice
                        generation
                        network
                        rarity
                        nextSummonTime
                        level
                        owner {
                        name
                    }
                    }
                }
                """
                result = requests.post(
                    GRAPHQL_URL, json={"query": query, "variables": variables}
                )
                current_heroes = result.json()
                current_heroes = current_heroes["data"]["heroes"]
                sale_heroes.extend(current_heroes)
                text_widget.insert(
                    tk.END, f"Total heroes for sale: {len(sale_heroes)}\n"
                )
                time.sleep(1)
                set_number += 1
                skip_number = set_number * 250

        all_heroes.extend(sale_heroes)

        return all_heroes

    def tavern_hire_query(variables, ability_queries, text_widget, all_heroes):
        hire_heroes = []
        text_widget.insert(tk.END, "Finding heroes on tavern for hire...\n")
        if "ability_list" in variables:
            for ability_query in ability_queries:
                set_number = 0
                skip_number = 0
                ability_filter = ability_query["filter"]
                while set_number == 0 or len(current_heroes) == 250:
                    variables["skip_number"] = skip_number
                    query = f"""
                        query saleAuctions($price_limit: String, $skip_number: Int!, $min_summon: Int, $max_summon: Int, $main_classes: [Int], $sub_classes: [Int], $max_generation: Int, $min_generation: Int, $max_rarity: Int, $min_rarity: Int, $max_level: Int, $min_level: Int, $ability_list: [Int]){{
                            heroes(first:250, skip: $skip_number, orderBy: id, orderDirection: desc, where: {{assistingPrice_not: null, assistingPrice_lte: $price_limit, summonsRemaining_gte: $min_summon, summonsRemaining_lte: $max_summon, mainClass_in: $main_classes, subClass_in: $sub_classes, generation_lte: $max_generation, generation_gte: $min_generation, rarity_lte: $max_rarity, rarity_gte: $min_rarity, level_lte: $max_level, level_gte: $min_level, {ability_filter}: $ability_list}}) {{
                                id
                                mainClass
                                subClass
                                summonsRemaining
                                passive1
                                passive2
                                active1
                                active2
                                assistingPrice
                                generation
                                network
                                statGenes
                                rarity
                                nextSummonTime
                                level
                                owner {{
                                    name
                                }}
                            }}
                        }}
                        """
                    result = requests.post(
                        GRAPHQL_URL, json={"query": query, "variables": variables}
                    )
                    result_json = result.json()
                    if "data" in result_json and "heroes" in result_json["data"]:
                        current_heroes = result.json()
                        current_heroes = current_heroes["data"]["heroes"]
                        hire_heroes.extend(current_heroes)
                        text_widget.insert(
                            tk.END, f"Total heroes for hire: {len(hire_heroes)}\n"
                        )
                    else:
                        text_widget.insert(
                            tk.END, f"Error in query response: {result_json}\n"
                        )
                    time.sleep(1)
                    set_number += 1
                    skip_number = set_number * 250
        else:
            set_number = 0
            skip_number = 0
            while set_number == 0 or len(current_heroes) == 250:
                variables["skip_number"] = skip_number
                query = """
                query saleAuctions($price_limit: String, $skip_number: Int!, $main_classes: [Int], $sub_classes: [Int], $max_summon: Int, $min_summon: Int, $max_generation: Int, $min_generation: Int, $max_rarity: Int, $min_rarity: Int, $max_level: Int, $min_level: Int){
                    heroes(first: 250, orderBy: id, skip: $skip_number, orderDirection: asc, where: {assistingPrice_not: null, assistingPrice_lte: $price_limit, mainClass_in: $main_classes, subClass_in: $sub_classes, summonsRemaining_gte: $min_summon, summonsRemaining_lte: $max_summon, generation_lte: $max_generation, generation_gte: $min_generation, rarity_lte: $max_rarity, rarity_gte: $min_rarity, level_lte: $max_level, level_gte: $min_level}
                    ) {
                        id
                        mainClass
                        subClass
                        summonsRemaining
                        passive1
                        passive2
                        active1
                        active2
                        assistingPrice
                        generation
                        network
                        rarity
                        nextSummonTime
                        level
                        owner {
                        name
                    }
                    }
                }
                """
                result = requests.post(
                    GRAPHQL_URL, json={"query": query, "variables": variables}
                )
                current_heroes = result.json()
                current_heroes = current_heroes["data"]["heroes"]
                hire_heroes.extend(current_heroes)
                text_widget.insert(
                    tk.END, f"Total heroes for hire: {len(hire_heroes)}\n"
                )
                time.sleep(1)
                set_number += 1
                skip_number = set_number * 250

        all_heroes.extend(hire_heroes)

        return all_heroes


class HeroSearchUI:
    """
    The main application class for the Hero Search User Interface.
    Initializes and manages the user interface components and handles user interactions.
    """

    def __init__(self, master):
        self.master = master
        self.master.title("Ratcrawler")
        self.master.configure(bg="black")
        self.master.geometry("1750x900")

        self.search_logic = SearchLogic()

        style = ttk.Style()
        style.configure("TFrame", background="black")
        style.configure(
            "TButton",
            background="black",
            foreground="white",
            borderwidth=1,
            focuscolor="none",
        )
        style.configure("TLabel", background="black", foreground="white")
        style.map(
            "TButton",
            background=[("active", "grey"), ("!disabled", "black")],
            foreground=[("active", "white")],
        )
        style.configure("TScale", background="black", foreground="white")
        style.configure(
            "TRadiobutton",
            background="black",
            foreground="white",
            indicatorbackground="black",
            indicatoron=False,
        )

        self.container = ttk.Frame(self.master, style="TFrame")
        self.container.pack(fill="both", expand=True)

        self.search_frame = ttk.Frame(self.container, style="TFrame")
        self.search_frame.pack(side="left", fill="y", padx=5, pady=0)

        self.results_frame = ttk.Frame(self.container, style="TFrame")
        self.results_frame.pack(side="right", fill="both", expand=True, padx=5, pady=0)

        self.video_frame = ttk.Frame(self.container, style="TFrame")
        self.video_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.rarity_map = {
            0: "common",
            1: "uncommon",
            2: "rare",
            3: "legendary",
            4: "mythic",
        }

        self.main_class_buttons = {}
        self.sub_class_buttons = {}
        self.class_names = {
            0: "Warrior",
            1: "Knight",
            2: "Thief",
            3: "Archer",
            4: "Priest",
            5: "Wizard",
            6: "Monk",
            7: "Pirate",
            8: "Berserker",
            9: "Seer",
            10: "Legionnaire",
            11: "Scholar",
            16: "Paladin",
            17: "DarkKnight",
            18: "Summoner",
            19: "Ninja",
            20: "Shapeshifter",
            21: "Bard",
            24: "Dragoon",
            25: "Sage",
            26: "Spellbow",
            28: "DreadKnight",
        }

        self.ability_names = {
            0: "B1",
            1: "B2",
            2: "B3",
            3: "B4",
            4: "B5",
            5: "B6",
            6: "B7",
            7: "B8",
            16: "A1",
            17: "A2",
            18: "A3",
            19: "A4",
            24: "E1",
            25: "E2",
            28: "T1",
        }

        self.main_class_selections = set()
        self.sub_class_selections = set()
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=0)
        self.container.grid_columnconfigure(1, weight=1)

        self.init_class_selection(
            self.search_frame,
            "Select Main Class",
            self.main_class_selections,
            0,
            is_main_class=True,
        )
        self.init_class_selection(
            self.search_frame,
            "Select Sub Class",
            self.sub_class_selections,
            1,
            is_main_class=False,
        )
        self.init_summon_selection(self.search_frame)
        self.init_generation_selection(self.search_frame)
        self.init_rarity_selection(self.search_frame)
        self.init_level_selection(self.search_frame)

        self.match_generation = tk.BooleanVar(value=False)
        self.match_summons = tk.BooleanVar(value=False)
        self.match_mainclass = tk.BooleanVar(value=False)
        self.match_subclass = tk.BooleanVar(value=False)
        self.match_sale = tk.BooleanVar(value=False)
        self.match_hire = tk.BooleanVar(value=False)
        self.ignore_cooldown = tk.BooleanVar(value=False)
        self.match_level = tk.BooleanVar(value=False)
        self.match_rarity = tk.BooleanVar(value=False)

        self.sale_price_limit_var = tk.StringVar(value="")
        self.hire_price_limit_var = tk.StringVar(value="")
        self.hero_id_var = tk.StringVar(value="")
        self.selected_ability = None

        self.init_sale_price_limit_input(self.search_frame)
        self.init_hire_price_limit_input(self.search_frame)
        self.init_hero_id_input(self.search_frame)
        self.init_generation_match_selection(self.search_frame)
        self.init_summons_match_selection(self.search_frame)
        self.init_mainclass_match_selection(self.search_frame)
        self.init_subclass_match_selection(self.search_frame)
        self.init_cooldown_selection(self.search_frame)
        self.init_level_match_selection(self.search_frame)
        self.init_rarity_match_selection(self.search_frame)

        self.ability_selections = {}
        self.init_ability_selection(self.search_frame)
        self.init_ability_match_slider(self.search_frame)

        self.search_button = tk.Button(
            self.search_frame,
            text="Search",
            bg="green",
            fg="white",
            highlightbackground="white",
            highlightcolor="white",
            highlightthickness=2,
            bd=5,
            command=self.perform_search,
        )
        self.search_button.grid(row=30, column=0, columnspan=4, pady=5)

        self.init_results_area()
        self.init_video_player()
        self.video_played = False

    def init_results_area(self):
        self.results_text = scrolledtext.ScrolledText(
            self.results_frame, width=150, height=20, bg="black", fg="white"
        )
        self.results_text.pack(fill="both", expand=True)
        self.results_text.config(state=tk.DISABLED)

        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(0, weight=1)

    def init_video_player(self):
        video_path = os.path.join(os.getcwd(), "shrek.mp4")
        self.video_player = VideoPlayer(self.video_frame, video_path, self.on_video_end)
        self.video_player.pack_forget()

    def on_video_end(self):
        self.video_frame.destroy()

    def perform_search(self):
        sale_price_limit = self.sale_price_limit_var.get().strip()
        hire_price_limit = self.hire_price_limit_var.get().strip()

        match_sale = bool(sale_price_limit)
        match_hire = bool(hire_price_limit)

        def run_search():
            all_heroes, results = self.search_logic.search_heroes(
                self.results_text,
                self.main_class_selections,
                self.sub_class_selections,
                self.min_summon_var.get(),
                self.max_summon_var.get(),
                self.min_generation_var.get(),
                self.max_generation_var.get(),
                self.min_rarity_var.get(),
                self.max_rarity_var.get(),
                self.min_level_var.get(),
                self.max_level_var.get(),
                self.match_level.get(),
                self.match_rarity.get(),
                self.match_summons.get(),
                self.match_generation.get(),
                self.match_mainclass.get(),
                self.match_subclass.get(),
                match_sale,
                self.ignore_cooldown.get(),
                self.sale_price_limit_var.get(),
                match_hire,
                self.hire_price_limit_var.get(),
                self.selected_ability,
                self.ability_match_num.get(),
                self.hero_id_var,
            )

            self.display_results(all_heroes, results)

        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)

        if not self.video_played:
            self.video_player.start()
            self.video_played = True

        search_thread = threading.Thread(target=run_search)
        search_thread.start()

    def display_results(self, all_heroes, matching_pairs):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)  # Clear existing content

        for i, (hero1_id, hero2_id, total_matches) in enumerate(matching_pairs[:250]):
            hero1 = next((hero for hero in all_heroes if hero["id"] == hero1_id), None)
            hero2 = next((hero for hero in all_heroes if hero["id"] == hero2_id), None)
            if hero1 and hero2:
                self.display_hero_pair(hero1, hero2, total_matches)

        self.results_text.config(state=tk.DISABLED)

    def display_hero_pair(self, hero1, hero2, total_matches):
        (
            hero1_info,
            hero1_abilities,
            priceinfo1,
            raritytag1,
        ) = self.construct_detailed_info(hero1)
        (
            hero2_info,
            hero2_abilities,
            priceinfo2,
            raritytag2,
        ) = self.construct_detailed_info(hero2)

        self.insert_hero_info(
            self.results_text,
            hero1_info,
            hero1_abilities,
            priceinfo1,
            raritytag1,
            hero1["owner"]["name"],
        )
        self.insert_hero_info(
            self.results_text,
            hero2_info,
            hero2_abilities,
            priceinfo2,
            raritytag2,
            hero2["owner"]["name"],
        )

        self.results_text.insert(tk.END, f"Total Matches: {total_matches} ")
        url = (
            f"https://dfk-adventures.herokuapp.com/heroes/{hero1['id']}/{hero2['id']}/"
        )
        hyperlink_text = "View on ADFK"
        tag_name = f"hyperlink_{hero1['id']}_{hero2['id']}"
        self.results_text.insert(tk.END, hyperlink_text + "\n", tag_name)
        self.results_text.tag_config(tag_name, foreground="#6495ED", underline=True)
        self.results_text.tag_bind(
            tag_name, "<Button-1>", lambda e, url=url: webbrowser.open_new_tab(url)
        )

    def insert_hero_info(
        self, text_widget, hero_info, abilities_info, priceinfo, rarity_tag, owner_name
    ):
        fixed_width = 13
        small_width = 2

        # Setup color tags for rarity and classes
        self.results_text.tag_config("common", foreground="white")
        self.results_text.tag_config("uncommon", foreground="lightgreen")
        self.results_text.tag_config("rare", foreground="blue")
        self.results_text.tag_config("legendary", foreground="orange")
        self.results_text.tag_config("mythic", foreground="purple")

        self.results_text.tag_config("basic_class", foreground="white")
        self.results_text.tag_config("advanced", foreground="green")
        self.results_text.tag_config("elite", foreground="#87CEEB")
        self.results_text.tag_config("transcendent", foreground="violet")

        # Extract hero information for display
        id_display = f"{hero_info['id']}".ljust(fixed_width)[:fixed_width]
        main_class_value = hero_info["mainClass"]
        subclass_value = hero_info["subClass"]
        main_class_display = (
            f"{self.class_names.get(main_class_value, 'Unknown Class'):<{fixed_width}}"
        )
        subclass_display = (
            f"{self.class_names.get(subclass_value, 'Unknown Class'):<{fixed_width}}"
        )
        gen_display = f"{hero_info['generation']:<{small_width}}"
        summons_display = f"{hero_info['summonsRemaining']:<{small_width}}"
        levels_display = f"{hero_info['level']:<{small_width}}"

        # Determine class tags
        main_class_tag = self.get_tag(main_class_value)
        subclass_tag = self.get_tag(subclass_value)

        # Insert hero information into the text widget
        text_widget.insert(tk.END, "ID: ")
        text_widget.insert(tk.END, id_display, rarity_tag)
        text_widget.insert(tk.END, " | Main Class: ")
        text_widget.insert(tk.END, main_class_display, main_class_tag)
        text_widget.insert(tk.END, "| Sub Class: ")
        text_widget.insert(tk.END, subclass_display, subclass_tag)
        text_widget.insert(tk.END, f" | Gen: {gen_display}")
        text_widget.insert(tk.END, f" | Summons: {summons_display}")
        text_widget.insert(tk.END, f" | Level: {levels_display}")

        # Insert abilities into the text widget
        self.insert_abilities_and_price(
            text_widget, abilities_info, priceinfo, owner_name
        )

    def get_tag(self, value):
        if value in range(16, 22):
            return "advanced"
        elif value in range(24, 27):
            return "elite"
        elif value in range(28, 30):
            return "transcendent"
        return "basic_class"

    def insert_abilities_and_price(
        self, text_widget, abilities_info, priceinfo, owner_name
    ):
        for ability_key, ability_value in abilities_info.items():
            text_widget.insert(tk.END, f" | {ability_key}: ")
            ability_name = self.ability_names.get(ability_value, "Unknown")
            ability_tag = self.get_tag(ability_value)
            text_widget.insert(tk.END, ability_name, ability_tag)

        text_widget.insert(tk.END, priceinfo)
        owner_name = owner_name if owner_name is not None else "None"
        text_widget.insert(tk.END, " | Owner: " + owner_name + "\n")

    def construct_detailed_info(self, hero):
        rarity = hero.get("rarity", 0)
        rarity_tags = {
            0: "common",
            1: "uncommon",
            2: "rare",
            3: "legendary",
            4: "mythic",
        }
        rarity_tag = rarity_tags.get(rarity, "common")

        hero_info = {
            "id": hero.get("id"),
            "mainClass": hero.get("mainClass"),
            "subClass": hero.get("subClass"),
            "generation": hero.get("generation", "Unknown"),
            "summonsRemaining": hero.get("summonsRemaining"),
            "level": hero.get("level"),
            "owner": hero.get("owner", {}).get("name"),
        }

        abilities_info = {
            "A1": hero.get("active1", "Unknown"),
            "A2": hero.get("active2", "Unknown"),
            "P1": hero.get("passive1", "Unknown"),
            "P2": hero.get("passive2", "Unknown"),
        }

        realm_info = ""
        if "salePrice" in hero or "assistingPrice" in hero:
            realm_info = f" | Realm: {hero.get('network', 'Unknown')}"
        if hero.get("network") == "kla":
            power_token = "Jade"
        elif hero.get("network") == "hmy":
            power_token = "Jewel"
        else:
            power_token = "Crystal"
        price_info = ""
        if "salePrice" in hero:
            price_gwei = int(hero["salePrice"]) / PRICE_MULTIPLIER
            price_info = f" | Sale: {price_gwei} {power_token}"
        elif "assistingPrice" in hero:
            price_gwei = int(hero["assistingPrice"]) / PRICE_MULTIPLIER
            price_info = f" | Hire: {price_gwei} {power_token}"

        combined_info = f"{realm_info}{price_info}"

        return hero_info, abilities_info, combined_info, rarity_tag

    def init_class_selection(
        self, master, label_text, selection_set, offset, is_main_class=True
    ):
        ttk.Label(master, text=label_text).grid(
            row=offset * 6, column=0, columnspan=4, sticky="w"
        )

        buttons_frame = ttk.Frame(master)
        buttons_frame.grid(row=1 + offset * 6, column=0, columnspan=4, sticky="ew")

        class_buttons = {}

        for index, (class_number, class_name) in enumerate(self.class_names.items()):
            btn = tk.Button(
                buttons_frame,
                text=f"{class_name}",
                bg="black",
                fg="white",
                highlightbackground="white",
                highlightcolor="white",
                highlightthickness=2,
                bd=5,
                command=lambda cn=class_number, s=selection_set: self.toggle_class_selection(
                    cn, s, class_buttons
                ),
            )
            btn.grid(
                row=(index // 4 + 1), column=index % 4, sticky="ew", padx=5, pady=0
            )
            class_buttons[class_number] = btn

        tk.Button(
            buttons_frame,
            text="All",
            command=lambda: self.select_classes(
                class_buttons, selection_set, list(self.class_names.keys())
            ),
        ).grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(
            buttons_frame,
            text="Basic",
            command=lambda: self.select_classes(
                class_buttons, selection_set, list(range(0, 12))
            ),
        ).grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(
            buttons_frame,
            text="Advanced",
            command=lambda: self.select_classes(
                class_buttons, selection_set, list(range(16, 22))
            ),
        ).grid(row=0, column=2, sticky="ew", padx=5)
        tk.Button(
            buttons_frame,
            text="Elite",
            command=lambda: self.select_classes(
                class_buttons, selection_set, list(range(24, 27))
            ),
        ).grid(row=0, column=3, sticky="ew", padx=5)

        buttons_frame.grid_columnconfigure(tuple(range(4)), weight=1)

    def init_summon_selection(self, master):
        ttk.Label(master, text="Summons Range:").grid(
            row=12, column=0, columnspan=4, sticky="w", padx=5
        )

        self.min_summon_var = tk.IntVar(value=0)
        ttk.Label(master, text="Min:").grid(row=13, column=0, sticky="w", padx=5)
        self.min_summon_label = ttk.Label(master, textvariable=self.min_summon_var)
        self.min_summon_label.grid(row=13, column=2, sticky="w")
        self.min_summon_scale = ttk.Scale(
            master,
            from_=0,
            to=11,
            orient="horizontal",
            variable=self.min_summon_var,
            command=self.update_summon_min_label,
        )
        self.min_summon_scale.grid(row=13, column=1, sticky="ew", padx=5)

        self.max_summon_var = tk.IntVar(value=11)
        ttk.Label(master, text="Max:").grid(row=14, column=0, sticky="w", padx=5)
        self.max_summon_label = ttk.Label(master, textvariable=self.max_summon_var)
        self.max_summon_label.grid(row=14, column=2, sticky="w")
        self.max_summon_scale = ttk.Scale(
            master,
            from_=0,
            to=11,
            orient="horizontal",
            variable=self.max_summon_var,
            command=self.update_summon_max_label,
        )
        self.max_summon_scale.grid(row=14, column=1, sticky="ew", padx=5)

    def init_generation_selection(self, master):
        master.columnconfigure(1, minsize=200)

        ttk.Label(master, text="Generation Range:").grid(
            row=15, column=0, columnspan=4, sticky="w", padx=5
        )

        self.min_generation_var = tk.IntVar(value=0)
        ttk.Label(master, text="Min:").grid(row=16, column=0, sticky="w", padx=5)
        self.min_generation_label = ttk.Label(
            master, textvariable=self.min_generation_var
        )
        self.min_generation_label.grid(row=16, column=2, sticky="w")
        self.min_generation_scale = ttk.Scale(
            master,
            from_=0,
            to=69,
            orient="horizontal",
            variable=self.min_generation_var,
            command=self.update_generation_min_label,
        )
        self.min_generation_scale.grid(row=16, column=1, sticky="ew", padx=5)

        self.max_generation_var = tk.IntVar(value=69)
        ttk.Label(master, text="Max:").grid(row=17, column=0, sticky="w", padx=5)
        self.max_generation_label = ttk.Label(
            master, textvariable=self.max_generation_var
        )
        self.max_generation_label.grid(row=17, column=2, sticky="w")
        self.max_generation_scale = ttk.Scale(
            master,
            from_=0,
            to=69,
            orient="horizontal",
            variable=self.max_generation_var,
            command=self.update_generation_max_label,
        )
        self.max_generation_scale.grid(row=17, column=1, sticky="ew", padx=5)

    def init_rarity_selection(self, master):
        ttk.Label(master, text="Rarity Range:").grid(
            row=18, column=0, columnspan=4, sticky="w", padx=5
        )
        self.min_rarity_name = tk.StringVar(value="common")
        self.max_rarity_name = tk.StringVar(value="mythic")

        self.min_rarity_var = tk.IntVar(value=0)
        ttk.Label(master, text="Min:").grid(row=19, column=0, sticky="w", padx=5)
        self.min_rarity_label = ttk.Label(master, textvariable=self.min_rarity_name)
        self.min_rarity_label.grid(row=19, column=2, sticky="w")
        self.min_rarity_scale = ttk.Scale(
            master,
            from_=0,
            to=4,
            orient="horizontal",
            variable=self.min_rarity_var,
            command=lambda e: self.update_rarity_labels(),
        )
        self.min_rarity_scale.grid(row=19, column=1, sticky="ew", padx=5)

        self.max_rarity_var = tk.IntVar(value=4)
        ttk.Label(master, text="Max:").grid(row=20, column=0, sticky="w", padx=5)
        self.max_rarity_label = ttk.Label(master, textvariable=self.max_rarity_name)
        self.max_rarity_label.grid(row=20, column=2, sticky="w")
        self.max_rarity_scale = ttk.Scale(
            master,
            from_=0,
            to=4,
            orient="horizontal",
            variable=self.max_rarity_var,
            command=lambda e: self.update_rarity_labels(),
        )
        self.max_rarity_scale.grid(row=20, column=1, sticky="ew", padx=5)

    def init_level_selection(self, master):
        ttk.Label(master, text="Level Range:").grid(
            row=21, column=0, columnspan=4, sticky="w", padx=5
        )

        self.min_level_var = tk.IntVar(value=1)
        ttk.Label(master, text="Min:").grid(row=22, column=0, sticky="w", padx=5)
        self.min_level_label = ttk.Label(master, textvariable=self.min_level_var)
        self.min_level_label.grid(row=22, column=2, sticky="w")
        self.min_level_scale = ttk.Scale(
            master,
            from_=1,
            to=20,
            orient="horizontal",
            variable=self.min_level_var,
            command=self.update_level_min_label,
        )
        self.min_level_scale.grid(row=22, column=1, sticky="ew", padx=5)

        self.max_level_var = tk.IntVar(value=20)
        ttk.Label(master, text="Max:").grid(row=23, column=0, sticky="w", padx=5)
        self.max_level_label = ttk.Label(master, textvariable=self.max_level_var)
        self.max_level_label.grid(row=23, column=2, sticky="w")
        self.max_level_scale = ttk.Scale(
            master,
            from_=1,
            to=20,
            orient="horizontal",
            variable=self.max_level_var,
            command=self.update_level_max_label,
        )
        self.max_level_scale.grid(row=23, column=1, sticky="ew", padx=5)

    def update_level_min_label(self, event=None):
        self.min_level_var.set(int(self.min_level_scale.get()))

    def update_level_max_label(self, event=None):
        self.max_level_var.set(int(self.max_level_scale.get()))

    def update_summon_min_label(self, event=None):
        self.min_summon_var.set(int(self.min_summon_scale.get()))

    def update_summon_max_label(self, event=None):
        self.max_summon_var.set(int(self.max_summon_scale.get()))

    def update_generation_min_label(self, event=None):
        self.min_generation_var.set(int(self.min_generation_scale.get()))

    def update_generation_max_label(self, event=None):
        self.max_generation_var.set(int(self.max_generation_scale.get()))

    def update_rarity_labels(self):
        min_rarity_value = self.min_rarity_var.get()
        max_rarity_value = self.max_rarity_var.get()

        rarity_map = {
            0: "common",
            1: "uncommon",
            2: "rare",
            3: "legendary",
            4: "mythic",
        }

        self.min_rarity_name.set(rarity_map.get(min_rarity_value, "Unknown"))
        self.max_rarity_name.set(rarity_map.get(max_rarity_value, "Unknown"))

    def toggle_class_selection(self, class_number, selection_set, class_buttons):
        if class_number in selection_set:
            selection_set.remove(class_number)
            new_color = "black"
        else:
            selection_set.add(class_number)
            new_color = "green"
        class_buttons[class_number].config(
            bg=new_color, fg="white", highlightbackground="white", highlightthickness=2
        )

    def select_classes(self, class_buttons, selection_set, class_range):
        """Toggle class selection based on the specified range."""
        for class_number in class_range:
            if class_number in class_buttons:
                if class_number in selection_set:
                    selection_set.remove(class_number)
                    class_buttons[class_number].config(
                        bg="black",
                        fg="white",
                        highlightbackground="white",
                        highlightthickness=2,
                    )
                else:
                    selection_set.add(class_number)
                    class_buttons[class_number].config(
                        bg="green",
                        fg="white",
                        highlightbackground="white",
                        highlightthickness=2,
                    )

    def init_hero_id_input(self, master):
        ttk.Label(master, text="Hero ID:").grid(
            row=21, column=2, sticky="e", padx=(70, 0)
        )
        self.hero_id_var = tk.StringVar()
        self.hero_id_entry = ttk.Entry(master, textvariable=self.hero_id_var)
        self.hero_id_entry.grid(row=21, column=3, sticky="ew", padx=(30, 0))

    def init_sale_price_limit_input(self, master):
        ttk.Label(master, text="Sale Price Limit:").grid(
            row=20, column=2, sticky="w", padx=(70, 0)
        )
        self.sale_price_limit_entry = ttk.Entry(
            master, textvariable=self.sale_price_limit_var, width=8
        )
        self.sale_price_limit_entry.grid(row=20, column=3, sticky="w", padx=(30, 0))

    def init_hire_price_limit_input(self, master):
        ttk.Label(master, text="Hire Price Limit:").grid(
            row=19, column=2, sticky="w", padx=(70, 0)
        )
        self.hire_price_limit_entry = ttk.Entry(
            master, textvariable=self.hire_price_limit_var, width=8
        )
        self.hire_price_limit_entry.grid(row=19, column=3, sticky="w", padx=(30, 0))

    def init_summons_match_selection(self, master):
        ttk.Label(master, text="Match Summons?").grid(
            row=12, column=2, columnspan=4, sticky="w", padx=(70, 0)
        )
        ttk.Radiobutton(
            master, text="Yes", variable=self.match_summons, value=True
        ).grid(row=12, column=3, sticky="w", padx=(30, 0))
        ttk.Radiobutton(
            master, text="No", variable=self.match_summons, value=False
        ).grid(row=12, column=3, sticky="w", padx=(75, 0))

    def init_generation_match_selection(self, master):
        ttk.Label(master, text="Match Generation?").grid(
            row=13, column=2, columnspan=4, sticky="w", padx=(70, 0)
        )
        ttk.Radiobutton(
            master, text="Yes", variable=self.match_generation, value=True
        ).grid(row=13, column=3, sticky="w", padx=(30, 0))
        ttk.Radiobutton(
            master, text="No", variable=self.match_generation, value=False
        ).grid(row=13, column=3, sticky="w", padx=(75, 0))

    def init_mainclass_match_selection(self, master):
        ttk.Label(master, text="Match MainClass?").grid(
            row=14, column=2, columnspan=4, sticky="w", padx=(70, 0)
        )
        ttk.Radiobutton(
            master, text="Yes", variable=self.match_mainclass, value=True
        ).grid(row=14, column=3, sticky="w", padx=(30, 0))
        ttk.Radiobutton(
            master, text="No", variable=self.match_mainclass, value=False
        ).grid(row=14, column=3, sticky="w", padx=(75, 0))

    def init_subclass_match_selection(self, master):
        ttk.Label(master, text="Match SubClass?").grid(
            row=15, column=2, columnspan=4, sticky="w", padx=(70, 0)
        )
        ttk.Radiobutton(
            master, text="Yes", variable=self.match_subclass, value=True
        ).grid(row=15, column=3, sticky="w", padx=(30, 0))
        ttk.Radiobutton(
            master, text="No", variable=self.match_subclass, value=False
        ).grid(row=15, column=3, sticky="w", padx=(75, 0))

    def init_cooldown_selection(self, master):
        ttk.Label(master, text="Ignore Cooldowns?").grid(
            row=16, column=2, columnspan=4, sticky="w", padx=(70, 0)
        )
        ttk.Radiobutton(
            master, text="Yes", variable=self.ignore_cooldown, value=True
        ).grid(row=16, column=3, sticky="w", padx=(30, 0))
        ttk.Radiobutton(
            master, text="No", variable=self.ignore_cooldown, value=False
        ).grid(row=16, column=3, sticky="w", padx=(75, 0))

    def init_rarity_match_selection(self, master):
        ttk.Label(master, text="Match Rarity?").grid(
            row=17, column=2, columnspan=4, sticky="w", padx=(70, 0)
        )
        ttk.Radiobutton(
            master, text="Yes", variable=self.match_rarity, value=True
        ).grid(row=17, column=3, sticky="w", padx=(30, 0))
        ttk.Radiobutton(
            master, text="No", variable=self.match_rarity, value=False
        ).grid(row=17, column=3, sticky="w", padx=(75, 0))

    def init_level_match_selection(self, master):
        ttk.Label(master, text="Match Level?").grid(
            row=18, column=2, columnspan=4, sticky="w", padx=(70, 0)
        )
        ttk.Radiobutton(master, text="Yes", variable=self.match_level, value=True).grid(
            row=18, column=3, sticky="w", padx=(30, 0)
        )
        ttk.Radiobutton(master, text="No", variable=self.match_level, value=False).grid(
            row=18, column=3, sticky="w", padx=(75, 0)
        )

    def init_ability_selection(self, master):
        ttk.Label(master, text="Ability Type:").grid(
            row=24, column=0, columnspan=4, sticky="w", padx=5
        )

        abilities = ["basic", "advanced", "elite"]
        buttons_frame = ttk.Frame(master)
        buttons_frame.grid(row=25, column=0, columnspan=3, sticky="ew")

        for index, ability in enumerate(abilities):
            btn = tk.Button(
                buttons_frame,
                text=ability,
                command=lambda a=ability: self.toggle_ability_selection(a),
            )
            btn.grid(row=0, column=index, sticky="ew", padx=5, pady=2)
            self.ability_selections[ability] = btn

        buttons_frame.grid_columnconfigure(tuple(range(len(abilities))), weight=1)

    def toggle_ability_selection(self, ability):
        if self.selected_ability == ability:
            self.ability_selections[ability].config(
                relief="raised", bg="SystemButtonFace"
            )
            self.selected_ability = None
        else:
            if self.selected_ability:
                self.ability_selections[self.selected_ability].config(
                    relief="raised", bg="SystemButtonFace"
                )
            self.ability_selections[ability].config(relief="sunken", bg="green")
            self.selected_ability = ability

    def init_ability_match_slider(self, master):
        ttk.Label(master, text="Ability Matches:").grid(
            row=24, column=3, columnspan=4, sticky="w", padx=5
        )

        self.ability_match_num = tk.IntVar(value=1)
        self.ability_match_slider = ttk.Scale(
            master,
            from_=1,
            to=4,
            orient="horizontal",
            variable=self.ability_match_num,
            command=self.update_ability_match_label,
        )
        self.ability_match_slider.grid(
            row=25, column=3, columnspan=4, sticky="ew", padx=5
        )

        self.ability_match_label = ttk.Label(
            master, textvariable=self.ability_match_num
        )
        self.ability_match_label.grid(row=25, column=4, sticky="w")

    def update_ability_match_label(self, event=None):
        self.ability_match_num.set(int(self.ability_match_slider.get()))


def main():
    global address_list
    address_file_path = os.path.join(os.getcwd(), "addresses.txt")
    address_list = read_addresses_from_file(address_file_path)
    root = tk.Tk()
    app = HeroSearchUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
