#!/usr/bin/env python3
"""Create Puerto Princesa content files using python-frontmatter."""

import frontmatter
import os

BASE_DIR = "/tmp/world66-f/content/asia/philippines/puerto_princesa"
os.makedirs(BASE_DIR, exist_ok=True)


def write_post(path, metadata, content):
    post = frontmatter.Post(content, **metadata)
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    print(f"Written: {path}")


# ── things_to_do.md ──────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/things_to_do.md",
    {"title": "Things to Do", "type": "section"},
    """\
Puerto Princesa's headline attraction is the [Subterranean River National Park](/asia/philippines/puerto_princesa/subterranean_river), a UNESCO World Heritage Site and one of the New Seven Wonders of Nature, where a navigable underground river winds through 8 km of cathedral-sized caverns before emptying into the sea. Permits and boat places are limited, so book well in advance — tours fill up days ahead during peak season.

Closer to the city, [Honda Bay](/asia/philippines/puerto_princesa/honda_bay) offers a full day of island-hopping across a scattering of coral-fringed islands, with snorkelling, a giant clam sanctuary, and clear shallow water that rewards those willing to hire a kayak for the afternoon. The [Iwahig Prison and Penal Farm](/asia/philippines/puerto_princesa/iwahig_prison) is one of the most unusual destinations in the Philippines — a low-security open colony where inmates farm the land and sell handicrafts to visitors.

The [Palawan Wildlife Rescue and Conservation Center](/asia/philippines/puerto_princesa/palawan_wildlife_center) is a genuine conservation operation (not a zoo) and the best place to see the Palawan bearcat, the rare Philippine crocodile, and other endemic species. The [Puerto Princesa City Baywalk](/asia/philippines/puerto_princesa/baywalk) stretches along the seafront and comes alive in the evening with local families, food stalls, and the sort of unhurried atmosphere that makes this city easy to like.
""",
)

# ── subterranean_river.md ─────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/subterranean_river.md",
    {
        "title": "Puerto Princesa Subterranean River National Park",
        "type": "poi",
        "tags": ["things_to_do", "sight", "wildlife", "nature"],
        "latitude": 10.1762,
        "longitude": 118.9183,
        "sources": [
            "https://en.wikipedia.org/wiki/Puerto_Princesa_Subterranean_River_National_Park"
        ],
        "story": (
            "When the park was being evaluated for the New Seven Wonders of Nature list in 2011, "
            "the Philippines government launched an unusually energetic public campaign to get votes. "
            "The country ended up delivering one of the highest vote totals in the competition — "
            "the river's win was partly a measure of how much Filipinos wanted the recognition."
        ),
    },
    """\
The Puerto Princesa Subterranean River is the longest navigable underground river in the world, running 8.2 km beneath the karst limestone mountains of the Saint Paul Mountain Range before emptying directly into the South China Sea. The river has been a UNESCO World Heritage Site since 1999 and was named one of the New Seven Wonders of Nature in 2011.

Guided bangka boats take visitors about 4 km into the cave system, where the river opens into chambers of extraordinary scale — some large enough to contain a cathedral. The formations include towering stalagmites, delicate stalactites, and cathedral-like domes. Nesting swiftlets and cave-dwelling bats are everywhere; the guano creates a rich if pungent ecosystem.

The park is 80 km from Puerto Princesa city. You need a permit (bought in advance online or through a tour operator) and a seat on one of the bangka boats that enter the cave — numbers are strictly controlled. Reaching the cave involves either joining an organised tour or taking a van to Sabang and then a 20-minute boat ride to the park entrance. The path through the jungle from Sabang to the beach is worth walking in its own right.
""",
)

# ── honda_bay.md ──────────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/honda_bay.md",
    {
        "title": "Honda Bay Island-Hopping",
        "type": "poi",
        "tags": ["things_to_do", "sight", "swimming", "nature"],
        "latitude": 10.0269,
        "longitude": 118.7931,
        "sources": [
            "https://en.wikipedia.org/wiki/Honda_Bay"
        ],
    },
    """\
Honda Bay is a sheltered body of water just north of Puerto Princesa city, scattered with small coral islands and sandbars accessible by bangka boat. Island-hopping day trips typically visit three or four islands: Starfish Island, Luli Island (which submerges at high tide, leaving only its nipa huts accessible by bamboo walkways), Cowrie Island, and Pandan Island.

The snorkelling is good rather than spectacular, and the islands themselves are low-key — no infrastructure beyond basic food stalls and changing huts. The appeal is the water: clear, warm, and shallow enough for non-swimmers to wade comfortably. Cowrie Island has a small giant clam sanctuary, a conservation project that gives a sense of the marine management effort in Palawan.

Tours leave from Santa Lourdes Port, about 15 km from the city centre. Most guest houses and tour operators in Puerto Princesa offer half-day and full-day packages, typically including a boat, guide, and basic lunch. Arriving early is worth it — the bay gets busier through the morning.
""",
)

# ── iwahig_prison.md ──────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/iwahig_prison.md",
    {
        "title": "Iwahig Prison and Penal Farm",
        "type": "poi",
        "tags": ["things_to_do", "sight", "historic_house"],
        "latitude": 9.5878,
        "longitude": 118.5275,
        "sources": [
            "https://en.wikipedia.org/wiki/Iwahig_Prison_and_Penal_Farm"
        ],
        "story": (
            "Established in 1904 under American colonial administration, Iwahig was deliberately "
            "designed as a self-sustaining prison colony where inmates farmed their own food and "
            "eventually earned the right to bring their families to live on the grounds. "
            "The philosophy — that rehabilitation was better served by open land than locked cells — "
            "was controversial in 1904 and remains unusual today."
        ),
    },
    """\
Iwahig is a low-security open prison colony covering some 37,000 hectares of farmland south of Puerto Princesa. Inmates — known as colonists — grow rice, vegetables, and fruit, and are free to move around the colony without guards. Some have brought their families to live with them on the grounds. The arrangement is closer to a small farming community than a conventional prison.

Visitors are welcome. The colony operates a small market where inmates sell rattan handicrafts, woven goods, and fresh produce. There is also a souvenir shop and, oddly, a dance troupe — on weekends, a group of inmates performs traditional Filipino dances for tourists. It is cheerful and a little surreal.

The colony is about 23 km south of Puerto Princesa city, reachable by tricycle or jeepney. No formal admission fee, though donations are appreciated. Bring respectful curiosity and leave the photography of individual inmates to their discretion.
""",
)

# ── palawan_wildlife_center.md ────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/palawan_wildlife_center.md",
    {
        "title": "Palawan Wildlife Rescue and Conservation Center",
        "type": "poi",
        "tags": ["things_to_do", "sight", "wildlife"],
        "latitude": 9.7388,
        "longitude": 118.7267,
        "sources": [
            "https://en.wikipedia.org/wiki/Palawan_Wildlife_Rescue_and_Conservation_Center"
        ],
    },
    """\
The Palawan Wildlife Rescue and Conservation Center — locally known as the Crocodile Farm, though that undersells it — is a government-run conservation facility on the edge of Puerto Princesa city. Its primary work is the captive breeding and rehabilitation of the critically endangered Philippine crocodile and the saltwater crocodile, with a view to eventual reintroduction.

The center also holds a range of other Palawan endemics: the Palawan bearcat (binturong), the Palawan peacock-pheasant, various pythons, and monitor lizards. The animals are not kept for show — the facility runs genuine research and rehabilitation programmes — but the enclosures are open to visitors and the guides know their subjects well.

The guided tour takes about an hour. The crocodile nursery, where hatchlings are kept in shallow tanks, is a highlight. The Philippine crocodile is one of the rarest reptiles in the world; there are perhaps a few hundred left in the wild. Seeing them up close, and understanding the effort going into saving them, is worth the admission.
""",
)

# ── baywalk.md ────────────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/baywalk.md",
    {
        "title": "Puerto Princesa City Baywalk",
        "type": "poi",
        "tags": ["things_to_do", "sight", "neighbourhood"],
        "latitude": 9.7469,
        "longitude": 118.7365,
        "sources": [
            "https://en.wikipedia.org/wiki/Puerto_Princesa"
        ],
    },
    """\
The baywalk runs along the waterfront of Puerto Princesa Bay, backed by gardens, food stalls, and the occasional monument. It is not a grand promenade — more of a well-maintained public space that genuinely belongs to the locals. In the late afternoon and evening, it fills with families, teenagers, and vendors selling grilled seafood and fresh buko juice.

The walking path stretches for about 2 km, offering views across the bay towards the mountains. At dusk, the light on the water is particularly good. There are shaded benches, playground equipment for children, and a small amphitheatre that hosts occasional performances.

The baywalk is a useful orientation point: the city centre is just a few blocks inland, and the tourist information office is nearby. It is the most pleasant way to spend an evening in Puerto Princesa if you are not heading out on a night tour.
""",
)

# ── eating_out.md ─────────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/eating_out.md",
    {"title": "Eating Out", "type": "section"},
    """\
Puerto Princesa has a solid eating scene by Philippine provincial standards, built around seafood and the distinctive freshwater fare of Palawan. The local speciality is tamilok, a woodworm harvested from mangrove roots, eaten raw with vinegar and chilli — an acquired taste that curious eaters tend to seek out once and remember for ever.

Look for restaurants along Rizal Avenue and the side streets near the baywalk, where turo-turo canteens (point-point diners where you indicate the dishes you want) serve honest rice meals at low prices alongside grilled fish, kinilaw, and sinigang. Seafood restaurants along the waterfront tend to be a step up in quality and price, and the freshness of the catch is generally excellent.
""",
)

# ── kinabuchs.md ──────────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/kinabuchs.md",
    {
        "title": "Kinabuch's Bar and Grill",
        "type": "poi",
        "tags": ["eating_out", "restaurant", "seafood"],
        "latitude": 9.7393,
        "longitude": 118.7343,
        "sources": [
            "https://en.wikipedia.org/wiki/Puerto_Princesa"
        ],
    },
    """\
Kinabuch's is a long-running Puerto Princesa institution on Rizal Avenue, popular with both locals and travellers. The menu leans heavily on Palawan seafood — grilled fish, prawns, and squid — alongside tamilok for the adventurous. The crocodile sisig, made from farmed crocodile meat, is a local talking point: the texture is somewhere between chicken and fish, and the flavour is mild enough to work in the calamansi-and-onion preparation.

The restaurant has a lively, open-air feel and serves ice-cold San Miguel from mid-morning. Prices are fair for the quality, and portions are generous. Reservations are not usually needed except on weekend evenings during peak season.
""",
)

# ── getting_there.md ──────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/getting_there.md",
    {"title": "Getting There", "type": "section"},
    """\
Puerto Princesa has its own international airport (PPS), about 2 km north of the city centre. Cebu Pacific, Philippine Airlines, and AirAsia all operate multiple daily flights from Manila, making it one of the better-connected provincial airports in the Philippines. Flight time from Manila is around 90 minutes. Direct flights also serve Cebu and a handful of other domestic routes.

Taxis and tricycles meet arriving flights at the airport and are the standard way to reach the city centre. Agree a price before getting in or insist on using the meter in metered cabs.

There is no practical overland route to Puerto Princesa from the rest of the Philippines; the city is only accessible by air or sea. Ferry services connect Puerto Princesa with Manila and a few other ports, but the journey takes 24 hours or more and is rarely chosen when flights are available.
""",
)

# ── getting_around.md ─────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/getting_around.md",
    {"title": "Getting Around", "type": "section"},
    """\
Puerto Princesa is a sprawling city but the main areas for visitors — the baywalk, Rizal Avenue, and the national highway — are manageable on foot or by tricycle. Tricycles (motorbike-with-sidecar) are the standard local transport; they are cheap, plentiful, and willing to negotiate rates for longer trips. Settle the price before departure.

Jeepneys serve fixed routes along the main highways and are the cheapest way to reach nearby areas. For day trips to Honda Bay, Iwahig, or the road towards Sabang, the easiest option is either hiring a tricycle for the whole day or joining a shared minivan tour — solo travellers on a budget can find fellow guests at most guesthouses to split costs.

For the Subterranean River, all visitors need to join an organised day trip or hire a van independently; the park is 80 km away and the logistics of the boat to the cave entrance are most easily handled through a tour operator. Many guesthouses arrange these directly.
""",
)

# ── when_to_go.md ─────────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/when_to_go.md",
    {"title": "When to Go", "type": "section"},
    """\
The dry season runs from November to May, with December through March offering the most reliably clear weather. This is peak tourist season, and boat trips, island-hopping, and the Subterranean River are all at their best. Book the river tour in advance during these months — available slots fill up quickly.

From June to October, the southwest monsoon brings heavy rain, rougher seas, and reduced visibility. Island-hopping in Honda Bay and boat access to the Subterranean River can be suspended on bad weather days. That said, the rains often come in afternoon storms rather than all-day downpours, and the city itself remains functional.

Puerto Princesa has less exposure to typhoons than the rest of the Philippines because of its position on the western coast, sheltered by Palawan's mountain spine. The city tends to experience tropical depressions rather than direct typhoon strikes, but travellers visiting between July and October should monitor weather forecasts and have flexible plans.
""",
)

# ── day_trips.md ──────────────────────────────────────────────────────────────
write_post(
    f"{BASE_DIR}/day_trips.md",
    {
        "title": "Day Trips",
        "type": "section",
        "linked_locations": [
            "asia/philippines/coron",
        ],
    },
    """\
Puerto Princesa is the practical gateway to [Palawan Island](/asia/philippines/palawanisland). Most travellers use it as a springboard: fly in, stay a night or two, do the Subterranean River, then head north by shared van to Port Barton or El Nido.

[Coron](/asia/philippines/coron), famous for its WWII wreck diving and the Kayangan and Barracuda lakes, is usually reached by air from Puerto Princesa rather than overland — the road north to Busuanga is long and rough. The flight takes about 40 minutes.
""",
)

print("\nAll files created successfully.")
