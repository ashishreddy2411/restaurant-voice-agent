"""
Restaurant Configuration
========================
Edit this file to update your restaurant's menu, hours, info, and agent personality.
No need to touch agent.py — just change things here and restart the agent.
"""

import os

# ─── Restaurant Info ──────────────────────────────────────────────────────────
# Basic details used in greetings and when callers ask general questions.
RESTAURANT_NAME = os.environ.get("RESTAURANT_NAME", "The Golden Fork")

RESTAURANT_INFO = {
    "name": RESTAURANT_NAME,
    "address": "123 Main Street, Downtown",
    "phone": "(555) 123-4567",
    "cuisine": "Contemporary American with Mediterranean influences",
    "hours": {
        "Monday–Thursday": "11:00 AM – 10:00 PM",
        "Friday–Saturday": "11:00 AM – 11:00 PM",
        "Sunday": "12:00 PM – 9:00 PM",
    },
    "reservation_policy": (
        "We hold reservations for 15 minutes past the booking time. "
        "Parties of 6 or more require a credit card to hold the table."
    ),
    "parking": "Free parking in our lot behind the building, plus street parking.",
    "dress_code": "Smart casual. No formal dress code required.",
}

# ─── Menu ─────────────────────────────────────────────────────────────────────
# Each item has:
#   name        → displayed to caller
#   price       → in USD (integer)
#   description → short, appetizing sentence
#   available   → set to False if the item is sold out or not available today
#
# To 86 an item (take it off for today): set "available": False
# To add a new item: copy any entry below and add it to the list

# ─── System Prompt ────────────────────────────────────────────────────────────
# Returns the agent's personality and rules, personalised with the caller's number.
# Called once per call from agent.py so every session has the right context.
def build_system_prompt(caller_number: str = "unknown") -> str:
    # On real phone calls caller_number is the caller's phone number.
    # On console/browser tests it will be "unknown".
    caller_context = (
        f"The caller's phone number is {caller_number}. "
        "Use this as their callback number for reservations unless they give you a different one."
        if caller_number not in ("unknown", "browser-test")
        else "This is a browser or console test session — ask for a callback number if taking a reservation."
    )

    return f"""
You are a warm, professional phone receptionist for {RESTAURANT_NAME}, a Contemporary American restaurant with Mediterranean influences.

{caller_context}

Your responsibilities:
1. Greet callers warmly and help them with their needs
2. Answer questions about the menu, hours, location, and policies — always use your tools, never guess
3. Take reservation requests — you MUST collect ALL of these before saving:
   - Guest name
   - Date (e.g. "this Saturday" or "March 20th")
   - Time (e.g. "7 PM")
   - Party size — ALWAYS ask this, never assume a number
   - Special requests (dietary restrictions, occasions) — optional, but ask
   - Callback number — use the caller's number unless they say otherwise
4. Repeat all details back to the caller and get confirmation before saving the reservation

Phone call rules:
- Be concise — 1 to 3 short sentences per reply. This is a phone call, not a chat.
- Speak naturally — no bullet points, no markdown, just conversational speech
- Ask for one piece of missing information at a time, not all at once
- Never guess at menu items, prices, or hours — always use a tool

Personality: warm and welcoming like a top-tier restaurant host. Knowledgeable, not pretentious.
""".strip()


# ─── Menu ─────────────────────────────────────────────────────────────────────
# Each item has:
#   name        → displayed to caller
#   price       → in USD (integer)
#   description → short, appetizing sentence
#   available   → set to False if the item is sold out or not available today
#
# To 86 an item (take it off for today): set "available": False
# To add a new item: copy any entry below and add it to the list
MENU: dict[str, list[dict]] = {
    "appetizers": [
        {
            "name": "Bruschetta al Pomodoro",
            "price": 12,
            "description": "Toasted sourdough, fresh heirloom tomatoes, basil, roasted garlic",
            "available": True,
        },
        {
            "name": "Calamari Fritti",
            "price": 15,
            "description": "Crispy fried calamari, house marinara, lemon aioli",
            "available": True,
        },
        {
            "name": "Burrata & Prosciutto",
            "price": 18,
            "description": "Fresh burrata, aged prosciutto, arugula, balsamic glaze",
            "available": False,  # 86'd today — change to True when back
        },
        {
            "name": "Soup of the Day",
            "price": 9,
            "description": "Chef's rotating daily selection — ask your server",
            "available": True,
        },
        {
            "name": "Shrimp Cocktail",
            "price": 17,
            "description": "Chilled jumbo shrimp, house cocktail sauce, lemon wedges",
            "available": True,
        },
    ],
    "mains": [
        {
            "name": "Grilled Salmon",
            "price": 32,
            "description": "Atlantic salmon, lemon butter sauce, seasonal vegetables, wild rice",
            "available": True,
        },
        {
            "name": "Filet Mignon 8oz",
            "price": 52,
            "description": "Grass-fed beef tenderloin, truffle butter, fingerling potatoes, asparagus",
            "available": True,
        },
        {
            "name": "Mushroom Risotto",
            "price": 24,
            "description": "Arborio rice, wild mushrooms, aged parmesan, white truffle oil (vegetarian)",
            "available": True,
        },
        {
            "name": "Chicken Piccata",
            "price": 26,
            "description": "Pan-seared chicken breast, lemon caper sauce, linguine",
            "available": True,
        },
        {
            "name": "Lobster Tagliatelle",
            "price": 45,
            "description": "Fresh Maine lobster, house-made tagliatelle, tomato cream sauce",
            "available": False,  # Out of lobster today
        },
        {
            "name": "Wagyu Smash Burger",
            "price": 22,
            "description": "8oz wagyu patty, aged cheddar, truffle aioli, brioche bun, hand-cut fries",
            "available": True,
        },
        {
            "name": "Grilled Branzino",
            "price": 36,
            "description": "Whole Mediterranean sea bass, herb olive oil, roasted cherry tomatoes, capers",
            "available": True,
        },
    ],
    "desserts": [
        {
            "name": "Tiramisu",
            "price": 11,
            "description": "Classic Italian — ladyfingers, mascarpone, espresso, cocoa",
            "available": True,
        },
        {
            "name": "Crème Brûlée",
            "price": 10,
            "description": "Vanilla bean custard with caramelized sugar crust",
            "available": True,
        },
        {
            "name": "Chocolate Lava Cake",
            "price": 12,
            "description": "Warm chocolate cake, molten dark chocolate center, vanilla gelato",
            "available": True,
        },
        {
            "name": "Seasonal Sorbet",
            "price": 8,
            "description": "Three scoops of house-made sorbet — rotating daily flavors",
            "available": True,
        },
    ],
    "drinks": [
        {
            "name": "Wine by the Glass",
            "price": 12,
            "description": "Curated red and white selections — ask for the wine list",
            "available": True,
        },
        {
            "name": "Craft Beer",
            "price": 9,
            "description": "Rotating local taps — ask for current selection",
            "available": True,
        },
        {
            "name": "Craft Cocktails",
            "price": 14,
            "description": "Seasonal cocktail menu — ask for highlights",
            "available": True,
        },
        {
            "name": "Mocktails",
            "price": 8,
            "description": "House-made non-alcoholic cocktails",
            "available": True,
        },
        {
            "name": "San Pellegrino",
            "price": 5,
            "description": "Sparkling mineral water, 750ml bottle",
            "available": True,
        },
    ],
}
