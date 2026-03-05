"""
Restaurant Configuration
========================
Edit this file to update your restaurant's menu, hours, info, and agent personality.
No need to touch agent.py — just change things here and restart the agent.

Quick-reference cheat sheet
----------------------------
  86 an item today       → set "available": False
  Restore an item        → set "available": True
  Add today's specials   → edit the SPECIALS list below
  Change hours           → edit RESTAURANT_INFO["hours"]
  Tweak agent tone       → edit build_system_prompt()
  Add a menu section     → add a new key + list to MENU (e.g. "sides")
"""

import os

# ─── Restaurant Info ──────────────────────────────────────────────────────────
# Shown to callers who ask general questions. Keep accurate — the agent reads
# directly from this dict and will quote it verbatim when relevant.

RESTAURANT_NAME = os.environ.get("RESTAURANT_NAME", "The Golden Fork")

RESTAURANT_INFO = {
    "name": RESTAURANT_NAME,
    "tagline": "Where American soul meets Mediterranean spirit.",
    "address": "123 Main Street, Downtown",
    "phone": "(555) 123-4567",
    "email": "hello@thegoldenfork.com",
    "website": "www.thegoldenfork.com",
    "instagram": "@thegoldenfork",
    "cuisine": "Contemporary American with Mediterranean influences",

    # ── Story / About ────────────────────────────────────────────────────────
    # Used when callers ask "what kind of place is this?" or "tell me about you"
    "about": (
        "The Golden Fork has been a Downtown institution since 2011. "
        "Chef Maria Sousa trained in Lisbon and New York before opening this "
        "neighborhood gem — a place where honest, seasonal ingredients meet "
        "bold Mediterranean technique. Whether you're celebrating or just hungry, "
        "we want every table to feel like the best seat in the house."
    ),

    # ── Hours ─────────────────────────────────────────────────────────────────
    "hours": {
        "Monday–Thursday": "11:00 AM – 10:00 PM",
        "Friday–Saturday": "11:00 AM – 11:00 PM",
        "Sunday": "12:00 PM – 9:00 PM",
    },
    "holiday_note": "We are closed Thanksgiving Day and Christmas Day.",
    "happy_hour": "Monday–Friday, 3:00 PM – 6:00 PM — $2 off all drinks and half-price bar bites.",

    # ── Policies ──────────────────────────────────────────────────────────────
    "reservation_policy": (
        "We hold reservations for 15 minutes past the booking time. "
        "Parties of 6 or more require a credit card to hold the table. "
        "Cancellations must be made at least 2 hours in advance."
    ),
    "waitlist_policy": (
        "Walk-ins are always welcome. On busy nights we run a waitlist — "
        "give us your number and we'll text you when your table is ready."
    ),
    "kids_policy": "Children are very welcome. High chairs and a kids' menu are available on request.",
    "dogs_policy": "Leashed dogs are welcome on our outdoor patio.",

    # ── Logistics ─────────────────────────────────────────────────────────────
    "parking": "Free parking in our lot behind the building, plus street parking on Main and Oak.",
    "accessibility": "Fully wheelchair accessible. Please let us know in advance for any other needs.",
    "dress_code": "Smart casual. No formal dress code required.",

    # ── Events & Private Dining ───────────────────────────────────────────────
    "private_dining": (
        "Our private dining room seats up to 30 guests and is available for "
        "corporate dinners, celebrations, and buyouts. Call or email to check availability."
    ),
    "events": (
        "We host a weekly wine dinner every Thursday at 7 PM and live jazz every "
        "Friday and Saturday from 8 PM. Reservations recommended."
    ),

    # ── Extras ────────────────────────────────────────────────────────────────
    "gift_cards": "Gift cards are available at the host stand, by phone, or on our website.",
    "catering": "We offer off-site catering for events of 20 or more. Email us for a quote.",
    "takeout": "Takeout is available Tuesday–Sunday. Call ahead or order on our website.",
}

# ─── Today's Specials ─────────────────────────────────────────────────────────
# Swap these out each morning. Leave empty if no specials today.
# "category" controls which section of the menu they appear under.

SPECIALS: list[dict] = [
    # {
    #     "name": "Pan-Seared Halibut",
    #     "price": 38,
    #     "description": "Fresh Pacific halibut, saffron beurre blanc, roasted fennel, grilled lemon",
    #     "category": "mains",
    #     "tags": ["gluten-free"],
    # },
    # {
    #     "name": "Strawberry Pavlova",
    #     "price": 13,
    #     "description": "Crisp meringue, whipped cream, fresh strawberries, mint",
    #     "category": "desserts",
    #     "tags": ["vegetarian", "gluten-free"],
    # },
]

# ─── Menu ─────────────────────────────────────────────────────────────────────
# Fields per item:
#   name        → read aloud to the caller
#   price       → in USD (integer)
#   description → one short, appetizing sentence
#   available   → False = 86'd today; flip back to True when restocked
#   tags        → helps the agent answer dietary questions accurately; use any of:
#                 "vegetarian", "vegan", "gluten-free", "contains-nuts",
#                 "spicy", "dairy-free", "contains-shellfish"

MENU: dict[str, list[dict]] = {

    # ── Appetizers ────────────────────────────────────────────────────────────
    "appetizers": [
        {
            "name": "Bruschetta al Pomodoro",
            "price": 12,
            "description": "Toasted sourdough, fresh heirloom tomatoes, basil, roasted garlic",
            "available": True,
            "tags": ["vegan"],
        },
        {
            "name": "Calamari Fritti",
            "price": 15,
            "description": "Crispy fried calamari, house marinara, lemon aioli",
            "available": True,
            "tags": [],
        },
        {
            "name": "Burrata & Prosciutto",
            "price": 18,
            "description": "Fresh burrata, aged prosciutto, arugula, balsamic glaze",
            "available": False,  # 86'd — restore when back in stock
            "tags": ["gluten-free"],
        },
        {
            "name": "Soup of the Day",
            "price": 9,
            "description": "Chef's rotating daily selection — ask your server for today's pick",
            "available": True,
            "tags": [],
        },
        {
            "name": "Shrimp Cocktail",
            "price": 17,
            "description": "Chilled jumbo shrimp, house cocktail sauce, lemon wedges",
            "available": True,
            "tags": ["gluten-free", "contains-shellfish"],
        },
        {
            "name": "Whipped Feta Dip",
            "price": 13,
            "description": "Whipped feta, honey, chilli flakes, warm pita bread",
            "available": True,
            "tags": ["vegetarian"],
        },
        {
            "name": "Tuna Crudo",
            "price": 19,
            "description": "Sashimi-grade tuna, yuzu vinaigrette, avocado, sesame, micro herbs",
            "available": True,
            "tags": ["gluten-free", "dairy-free"],
        },
        {
            "name": "Crispy Artichoke Hearts",
            "price": 14,
            "description": "Fried baby artichokes, lemon zest, shaved parmesan, herb aioli",
            "available": True,
            "tags": ["vegetarian"],
        },
    ],

    # ── Salads ────────────────────────────────────────────────────────────────
    "salads": [
        {
            "name": "Golden Fork House Salad",
            "price": 13,
            "description": "Mixed greens, shaved fennel, radish, cucumber, champagne vinaigrette",
            "available": True,
            "tags": ["vegan", "gluten-free"],
        },
        {
            "name": "Classic Caesar",
            "price": 15,
            "description": "Romaine hearts, house-made Caesar dressing, parmesan crisp, focaccia croutons",
            "available": True,
            "tags": ["vegetarian"],
        },
        {
            "name": "Warm Lentil & Roasted Beet",
            "price": 16,
            "description": "French lentils, roasted golden beets, goat cheese, walnuts, sherry vinaigrette",
            "available": True,
            "tags": ["vegetarian", "gluten-free", "contains-nuts"],
        },
        {
            "name": "Grilled Halloumi & Watermelon",
            "price": 17,
            "description": "Charred halloumi, seedless watermelon, mint, toasted pine nuts, pomegranate molasses",
            "available": True,
            "tags": ["vegetarian", "gluten-free", "contains-nuts"],
        },
    ],

    # ── Mains ─────────────────────────────────────────────────────────────────
    "mains": [
        {
            "name": "Grilled Salmon",
            "price": 32,
            "description": "Atlantic salmon, lemon butter sauce, seasonal vegetables, wild rice",
            "available": True,
            "tags": ["gluten-free"],
        },
        {
            "name": "Filet Mignon 8oz",
            "price": 52,
            "description": "Grass-fed beef tenderloin, truffle butter, fingerling potatoes, asparagus",
            "available": True,
            "tags": ["gluten-free"],
        },
        {
            "name": "Mushroom Risotto",
            "price": 24,
            "description": "Arborio rice, wild mushrooms, aged parmesan, white truffle oil",
            "available": True,
            "tags": ["vegetarian", "gluten-free"],
        },
        {
            "name": "Chicken Piccata",
            "price": 26,
            "description": "Pan-seared chicken breast, lemon caper sauce, linguine",
            "available": True,
            "tags": [],
        },
        {
            "name": "Lobster Tagliatelle",
            "price": 45,
            "description": "Fresh Maine lobster, house-made tagliatelle, tomato cream sauce",
            "available": False,  # Out of lobster — restore when restocked
            "tags": ["contains-shellfish"],
        },
        {
            "name": "Wagyu Smash Burger",
            "price": 22,
            "description": "8oz wagyu patty, aged cheddar, truffle aioli, brioche bun, hand-cut fries",
            "available": True,
            "tags": [],
        },
        {
            "name": "Grilled Branzino",
            "price": 36,
            "description": "Whole Mediterranean sea bass, herb olive oil, roasted cherry tomatoes, capers",
            "available": True,
            "tags": ["gluten-free", "dairy-free"],
        },
        {
            "name": "Moroccan Spiced Lamb Chops",
            "price": 46,
            "description": "Double-cut lamb chops, harissa glaze, couscous, preserved lemon yoghurt",
            "available": True,
            "tags": [],
        },
        {
            "name": "Eggplant Parmigiana",
            "price": 22,
            "description": "Slow-roasted aubergine, San Marzano tomato, fresh mozzarella, fresh basil",
            "available": True,
            "tags": ["vegetarian"],
        },
        {
            "name": "Seared Duck Breast",
            "price": 38,
            "description": "Magret duck, cherry reduction, creamy polenta, roasted root vegetables",
            "available": True,
            "tags": ["gluten-free"],
        },
    ],

    # ── Sides ─────────────────────────────────────────────────────────────────
    "sides": [
        {
            "name": "Hand-Cut Fries",
            "price": 7,
            "description": "Crispy fries, sea salt, house aioli",
            "available": True,
            "tags": ["vegan", "gluten-free"],
        },
        {
            "name": "Roasted Seasonal Vegetables",
            "price": 8,
            "description": "Chef's selection of roasted market vegetables, herb oil",
            "available": True,
            "tags": ["vegan", "gluten-free"],
        },
        {
            "name": "Truffle Mac & Cheese",
            "price": 10,
            "description": "Cavatappi pasta, four-cheese sauce, black truffle, toasted breadcrumbs",
            "available": True,
            "tags": ["vegetarian"],
        },
        {
            "name": "Warm Pita Bread",
            "price": 5,
            "description": "House-made pita, served warm with whipped butter",
            "available": True,
            "tags": ["vegetarian"],
        },
        {
            "name": "Creamy Polenta",
            "price": 8,
            "description": "Stone-ground polenta, parmesan, chive butter",
            "available": True,
            "tags": ["vegetarian", "gluten-free"],
        },
    ],

    # ── Desserts ──────────────────────────────────────────────────────────────
    "desserts": [
        {
            "name": "Tiramisu",
            "price": 11,
            "description": "Classic Italian — ladyfingers, mascarpone, espresso, cocoa",
            "available": True,
            "tags": ["vegetarian"],
        },
        {
            "name": "Crème Brûlée",
            "price": 10,
            "description": "Vanilla bean custard with a caramelised sugar crust",
            "available": True,
            "tags": ["vegetarian", "gluten-free"],
        },
        {
            "name": "Chocolate Lava Cake",
            "price": 12,
            "description": "Warm dark chocolate cake with a molten centre, vanilla gelato",
            "available": True,
            "tags": ["vegetarian"],
        },
        {
            "name": "Seasonal Sorbet",
            "price": 8,
            "description": "Three scoops of house-made sorbet — rotating daily flavours",
            "available": True,
            "tags": ["vegan", "gluten-free"],
        },
        {
            "name": "Baklava Cheesecake",
            "price": 13,
            "description": "New York cheesecake base, honey-pistachio baklava topping, rose water cream",
            "available": True,
            "tags": ["vegetarian", "contains-nuts"],
        },
        {
            "name": "Affogato",
            "price": 9,
            "description": "Double espresso poured over vanilla gelato — simple, perfect",
            "available": True,
            "tags": ["vegetarian", "gluten-free"],
        },
    ],

    # ── Drinks ────────────────────────────────────────────────────────────────
    "drinks": [
        {
            "name": "Wine by the Glass",
            "price": 12,
            "description": "Curated red and white selections — ask for the wine list",
            "available": True,
            "tags": ["vegan"],
        },
        {
            "name": "Craft Beer",
            "price": 9,
            "description": "Rotating local taps — ask for tonight's selection",
            "available": True,
            "tags": [],
        },
        {
            "name": "Craft Cocktails",
            "price": 14,
            "description": "Seasonal cocktail menu — ask for tonight's highlights",
            "available": True,
            "tags": [],
        },
        {
            "name": "Mocktails",
            "price": 8,
            "description": "House-made non-alcoholic cocktails, just as inventive",
            "available": True,
            "tags": ["vegan"],
        },
        {
            "name": "San Pellegrino",
            "price": 5,
            "description": "Sparkling mineral water, 750 ml bottle",
            "available": True,
            "tags": ["vegan", "gluten-free"],
        },
        {
            "name": "Still Water",
            "price": 3,
            "description": "Filtered still water, 750 ml bottle",
            "available": True,
            "tags": ["vegan", "gluten-free"],
        },
        {
            "name": "Soft Drinks",
            "price": 4,
            "description": "Coke, Diet Coke, Sprite, lemonade — free refills",
            "available": True,
            "tags": ["vegan"],
        },
        {
            "name": "Coffee & Tea",
            "price": 4,
            "description": "Drip coffee, espresso, cappuccino, or selection of loose-leaf teas",
            "available": True,
            "tags": ["vegan"],
        },
    ],
}

# ─── Helper: merge menu + specials ────────────────────────────────────────────
# The agent calls this instead of reading MENU directly so specials are always
# included. You don't need to edit this function.

def get_full_menu() -> dict[str, list[dict]]:
    """Return the main MENU merged with today's SPECIALS."""
    full = {section: list(items) for section, items in MENU.items()}
    for special in SPECIALS:
        section = special.get("category", "mains")
        entry = {k: v for k, v in special.items() if k != "category"}
        entry.setdefault("available", True)
        entry.setdefault("tags", ["special"])
        full.setdefault(section, []).append(entry)
    return full


# ─── System Prompt ────────────────────────────────────────────────────────────
# This defines who the agent IS and how it behaves on every call.
# Personality changes go here — agent.py just calls this function.

def build_system_prompt(caller_number: str = "unknown") -> str:
    """Return a fully-formed system prompt personalised for this caller."""

    # Caller context — used in the reservation flow
    if caller_number not in ("unknown", "browser-test"):
        caller_context = (
            f"The caller's phone number is {caller_number}. "
            "Use it as their callback number unless they give you a different one."
        )
    else:
        caller_context = (
            "This is a browser or console test — no real phone number is available. "
            "Ask for a callback number if you're taking a reservation."
        )

    # Build sections — only include specials line when there are actual specials
    sections = [
        f"You are Vera, the phone host at {RESTAURANT_NAME} — a beloved Downtown restaurant where American comfort meets Mediterranean craft. You've worked here for years and know this place inside and out: the stories behind the dishes, the regulars, the rhythm of a busy Friday night.",
        caller_context,
    ]
    if SPECIALS:
        sections.append(
            "Today's specials are: "
            + "; ".join(f"{s['name']} at ${s['price']} — {s['description']}" for s in SPECIALS)
            + ". Mention these naturally when callers ask for recommendations or about the menu."
        )

    return "\n\n".join(sections) + """

== YOUR RESPONSIBILITIES ==

1. Greet every caller warmly. Once you know their name, use it naturally — not on every sentence, just where it feels right.

2. Answer questions about the menu, hours, location, and policies — ALWAYS use your tools. Never answer from memory. Call the tool, then speak from what it returns.

3. Handle reservations. Collect ALL of the following before confirming:
      • Guest name
      • Date  (e.g. "this Saturday" or "March 20th")
      • Time  (e.g. "7 PM")
      • Party size — always ask; never assume
      • Special requests — dietary needs, celebrations, accessibility (ask warmly, not like a form)
      • Callback number — use the caller's number unless they say otherwise
   Read every detail back and get explicit confirmation before saving.

4. Handle complaints graciously. Acknowledge the feeling first, then solve the problem. If it's beyond your power, offer to leave a message for the manager.

5. If a caller mentions a special occasion — birthday, anniversary, proposal — respond warmly and offer to flag it for the kitchen or front-of-house team.

== TOOL ROUTING — CALL THESE EVERY TIME, NO EXCEPTIONS ==

Never answer any of the following from memory. Always call the tool first:

• Happy hour, drink deals, discounts on drinks → get_restaurant_info("happy_hour")
• Hours, when open, closing time → get_restaurant_info("hours")
• Events, jazz, live music, wine dinner → get_restaurant_info("events")
• Kids, children, high chairs, family → get_restaurant_info("kids_policy")
• Dogs, pets, animals, outdoor patio → get_restaurant_info("dogs_policy")
• Parking → get_restaurant_info("parking")
• Private dining, private room, large group event → get_restaurant_info("private_dining")
• Wheelchair, accessible, mobility needs → get_restaurant_info("accessibility")
• Catering, off-site → get_restaurant_info("catering")
• Takeout, to-go, pick-up → get_restaurant_info("takeout")
• Gift cards → get_restaurant_info("gift_cards")
• Cancellation, cancel a reservation → get_restaurant_info("reservation_policy")
• Walk-in, no reservation, wait list → get_restaurant_info("waitlist_policy")
• Dress code → get_restaurant_info("dress_code")
• About the restaurant, the chef, the story → get_restaurant_info("about")
• Drinks, alcohol, wine, beer, cocktails, coffee, tea → get_menu_items("drinks")
• Dietary questions (vegetarian, vegan, gluten-free, allergies) → get_menu_items("all")
• Any specific dish or price → check_item_availability("dish name")

== ACCURACY RULE — THIS IS CRITICAL ==

When a tool returns a price, time, or policy text: state those values VERBATIM.
Do NOT round, estimate, or rephrase numbers. If the tool says $52, say "fifty-two dollars" — not "around fifty" or "$50".
If the tool says "Monday–Friday, 3:00 PM – 6:00 PM", repeat exactly that.
Your credibility depends entirely on accuracy.

== PHONE CALL RULES ==

- Keep replies short: 1–3 sentences. This is a phone call, not a chat.
- Speak naturally — no bullet points, no markdown, no lists. Pure spoken English.
- Ask ONE question per turn. Never stack multiple questions.
- End every call warmly: "We look forward to seeing you!" or "Call us anytime!"

== PERSONALITY & TONE ==

You are warm, quick-witted, and quietly confident — the kind of host people remember long after the meal. You love this restaurant and it shows. You are never robotic, never stiff, never rushing through a script. You adapt: efficient with a caller who knows what they want, warm and unhurried with someone who wants a recommendation.

Use natural spoken language: contractions ("we'd love to", "I'll check on that"), brief affirmations ("Of course!", "Absolutely!") — but vary them, never repeat the same phrase twice in a row.

For recommendations: always call check_item_availability first. You love the Wagyu Burger and the Chocolate Lava Cake. For special occasions, suggest the Filet Mignon or Chef Maria's Grilled Branzino. The Baklava Cheesecake is the best dessert on the menu — just confirm it's available first.

== EXAMPLE CONVERSATIONS ==
(These demonstrate correct tool use, accuracy, and tone. Do not quote them verbatim — just follow the same pattern.)

Example 1 — Happy hour question:
Caller: "Do you have a happy hour?"
[Immediately call get_restaurant_info("happy_hour"). Then speak from the result.]
Vera: "We do! Happy hour runs Monday through Friday, three to six PM — two dollars off all drinks and half-price bar bites. A great time to come in."

Example 2 — Price question:
Caller: "How much is the Filet Mignon?"
[Call check_item_availability("Filet Mignon"). Read the price verbatim from the result.]
Vera: "The Filet Mignon is fifty-two dollars — an eight-ounce grass-fed tenderloin with truffle butter and fingerling potatoes. It's really special."

Example 3 — Natural reservation with a celebration:
Caller: "I'd like to make a reservation."
Vera: "I'd love to help! What date were you thinking?"
Caller: "This Saturday."
Vera: "Perfect — and what time works for you?"
Caller: "Seven PM."
Vera: "And how many people will be joining you?"
Caller: "Just the two of us."
Vera: "Wonderful. Can I get your name?"
Caller: "It's Maya."
Vera: "Any special requests, Maya — dietary needs or maybe a celebration?"
Caller: "It's actually our anniversary."
Vera: "How lovely! I'll make sure the team knows. So that's a table for two on Saturday at seven PM under Maya, and we'll flag the anniversary. Does that all look right?"
Caller: "Yes, perfect."
[Call save_reservation with all confirmed details.]
Vera: "You're all set! We'll look forward to celebrating with you Saturday evening."
""".strip()