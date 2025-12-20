# app/nlu.py
# Natural Language Understanding - Parse user queries to extract intent, topic, and time range
# Comprehensive entity-aware detection for all topics

import re
from dataclasses import dataclass
from typing import Literal, Optional, List, Dict
from .config import TOPIC_SUBREDDIT_MAP

TimeRange = Literal["hour", "day", "week", "month", "year", "all"]
Intent = Literal["summarize", "highlights", "trending", "compare", "help", "settings"]


@dataclass
class ParsedQuery:
    """Parsed user query with extracted parameters."""
    topic: str                      # e.g., "ai", "tech"
    subreddits: list[str]           # e.g., ["MachineLearning", "ChatGPT"]
    time_range: TimeRange           # e.g., "week"
    intent: Intent                  # e.g., "summarize"
    original_query: str             # Original user input
    language: str                   # Always "en"
    limit: int                      # Number of posts to fetch
    detected_entities: list[str]    # Specific entities found (games, coins, models, etc.)


# =============================================================================
# COMPREHENSIVE TOPIC KEYWORDS & ENTITIES
# =============================================================================

TOPIC_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "ai": {
        "keywords": [
            r"\bai\b", r"artificial intelligence", r"machine learning", r"\bml\b",
            r"\bllm\b", r"deep learning", r"neural network", r"transformer",
            r"natural language", r"computer vision", r"generative ai", r"gen ai",
        ],
        "entities": [
            # Models
            r"\bgpt[-\s]?[234o]?\b", r"chatgpt", r"openai", r"\bclaude\b", r"anthropic",
            r"\bgemini\b", r"\bllama\b", r"meta ai", r"\bmistral\b", r"\bcohere\b",
            r"stable diffusion", r"midjourney", r"dall[-\s]?e", r"\bsora\b",
            r"copilot", r"hugging\s?face", r"\bgrok\b", r"perplexity",
            # Concepts
            r"finetuning", r"fine[-\s]?tuning", r"prompt engineering", r"rag\b",
            r"vector database", r"embedding", r"inference", r"training run",
            r"rlhf", r"alignment", r"hallucination", r"context window",
        ],
    },
    
    "tech": {
        "keywords": [
            r"\btech\b", r"technology", r"gadgets?", r"hardware", r"software",
            r"smartphone", r"laptop", r"computer", r"device", r"chip",
        ],
        "entities": [
            # Companies
            r"\bapple\b", r"\bgoogle\b", r"\bmicrosoft\b", r"\bamazon\b", r"\bmeta\b",
            r"\bnvidia\b", r"\bintel\b", r"\bamd\b", r"\bqualcomm\b", r"\bsamsumg\b",
            r"\btsmc\b", r"\bdell\b", r"\bhp\b", r"\blenovo\b", r"\basus\b",
            # Products
            r"iphone", r"ipad", r"macbook", r"imac", r"airpods", r"apple watch",
            r"pixel", r"android", r"windows", r"linux", r"macos", r"ios",
            r"\bcpu\b", r"\bgpu\b", r"graphics card", r"processor", r"m[1234] chip",
            r"rtx", r"geforce", r"radeon", r"ryzen", r"threadripper",
            r"usb[-\s]?c", r"thunderbolt", r"wifi", r"5g", r"starlink",
        ],
    },
    
    "programming": {
        "keywords": [
            r"programming", r"\bcode\b", r"\bcoding\b", r"developer", r"software dev",
            r"web dev", r"backend", r"frontend", r"full[-\s]?stack", r"\bapi\b",
            r"\bbug\b", r"debug", r"deploy", r"devops", r"ci/cd",
        ],
        "entities": [
            # Languages
            r"\bpython\b", r"\bjavascript\b", r"\btypescript\b", r"\bjava\b",
            r"\bc\+\+\b", r"\bc#\b", r"\brust\b", r"\bgo\b", r"\bkotlin\b",
            r"\bswift\b", r"\bruby\b", r"\bphp\b", r"\bscala\b", r"\bzig\b",
            # Frameworks/Tools
            r"\breact\b", r"\bvue\b", r"\bangular\b", r"\bsvelte\b", r"\bnext\.?js\b",
            r"\bnode\.?js\b", r"\bdjango\b", r"\bflask\b", r"\bfastapi\b",
            r"\bspring\b", r"\brails\b", r"\blasravel\b", r"\bdocker\b",
            r"\bkubernetes\b", r"\bgit\b", r"\bgithub\b", r"\bgitlab\b",
            r"stack\s?overflow", r"\bnpm\b", r"\bpip\b", r"\bcargo\b",
            r"\baws\b", r"\bazure\b", r"\bgcp\b", r"cloud",
        ],
    },
    
    "sports": {
        "keywords": [
            r"\bsports?\b", r"\bfootball\b", r"\bsoccer\b", r"\bbasketball\b",
            r"\btennis\b", r"\bgolf\b", r"\bbaseball\b", r"\bhockey\b",
            r"\brugby\b", r"\bcricket\b", r"\bf1\b", r"formula\s?1", r"\bmma\b",
            r"\bufc\b", r"\bboxing\b", r"\bolympics\b", r"world cup",
        ],
        "entities": [
            # Leagues/Competitions
            r"\bnba\b", r"\bnfl\b", r"\bmlb\b", r"\bnhl\b", r"\bmls\b",
            r"premier league", r"\bucl\b", r"champions league", r"\bla liga\b",
            r"\bbundesliga\b", r"\bserie a\b", r"\bligue 1\b", r"\beuro\b",
            r"super bowl", r"world series", r"stanley cup", r"march madness",
            # Teams (major)
            r"lakers", r"celtics", r"warriors", r"bulls", r"heat",
            r"manchester (united|city)", r"\breal madrid\b", r"\bbarcelona\b",
            r"\bliverpool\b", r"\bchelsea\b", r"\barsenal\b", r"\btottenham\b",
            r"\bjuventus\b", r"\bbayern\b", r"\bpsg\b", r"\bdortmund\b",
            r"cowboys", r"patriots", r"chiefs", r"49ers", r"packers",
            r"yankees", r"dodgers", r"red sox",
            # Athletes
            r"\bmessi\b", r"\bronaldo\b", r"\bneymar\b", r"\bmbappe\b",
            r"\blebron\b", r"\bcurry\b", r"\bdurant\b", r"\bgiannis\b",
            r"\bmahomes\b", r"\bbrady\b", r"\bohtani\b", r"\bjudge\b",
        ],
    },
    
    "politics": {
        "keywords": [
            r"politic", r"government", r"election", r"vote", r"voting",
            r"democrat", r"republican", r"congress", r"parliament",
            r"legislation", r"law", r"policy", r"foreign affairs",
        ],
        "entities": [
            # US Politics
            r"\btrump\b", r"\bbiden\b", r"\bharris\b", r"\bobama\b",
            r"white house", r"\bsenate\b", r"house of rep", r"\bgop\b",
            r"supreme court", r"\bscotus\b", r"mid[-\s]?terms?",
            # World leaders / figures
            r"\bputin\b", r"\bzelensky\b", r"\bmacron\b", r"\bscholz\b",
            r"\bsunak\b", r"\bstarmer\b", r"\bnetanyahu\b", r"\bxi\b",
            r"\bun\b", r"\bnato\b", r"\beu\b", r"european union",
            # Topics
            r"abortion", r"immigration", r"gun control", r"climate",
            r"healthcare", r"tax", r"tariff", r"sanction", r"impeach",
            r"left[-\s]?wing", r"right[-\s]?wing", r"progressive", r"conservative",
        ],
    },
    
    "gaming": {
        "keywords": [
            r"\bgaming\b", r"video\s?game", r"\bgamers?\b", r"\besports?\b",
            r"play\s?through", r"speedrun", r"mod(ding)?", r"dlc",
        ],
        "entities": [
            # Platforms
            r"\bps5\b", r"playstation", r"\bxbox\b", r"\bswitch\b", r"\bpc gaming\b",
            r"\bsteam\b", r"\bepic games\b", r"game pass", r"\bnintendo\b",
            r"\bsony\b", r"\bvr\b", r"oculus", r"quest", r"steam deck",
            # Publishers/Studios
            r"\bea\b", r"electronic arts", r"\bubisoft\b", r"\bactivision\b",
            r"\bblizzard\b", r"\bbethesda\b", r"\brockstar\b", r"\bnaughty dog\b",
            r"\bfromsoft", r"\bnintendo\b", r"\bvalve\b", r"\briot\b",
            # Games (popular/recent)
            r"baldur'?s gate", r"elden ring", r"cyberpunk", r"starfield",
            r"gta", r"call of duty", r"\bcod\b", r"fortnite", r"minecraft",
            r"zelda", r"tears of the kingdom", r"totk", r"botw",
            r"final fantasy", r"ffxiv", r"ffxvi", r"diablo", r"world of warcraft",
            r"\bwow\b", r"overwatch", r"valorant", r"league of legends", r"\blol\b",
            r"counter[-\s]?strike", r"\bcs2\b", r"\bcsgo\b", r"apex legends",
            r"hogwarts legacy", r"spider[-\s]?man", r"god of war", r"\bhalo\b",
            r"game awards", r"goty", r"game of the year",
        ],
    },
    
    "crypto": {
        "keywords": [
            r"\bcrypto\b", r"cryptocurrency", r"blockchain", r"decentralized",
            r"\bdefi\b", r"\bnft\b", r"web3", r"token", r"mining",
            r"\bhodl\b", r"bull run", r"bear market",
        ],
        "entities": [
            # Coins
            r"\bbitcoin\b", r"\bbtc\b", r"\bethereum\b", r"\beth\b",
            r"\bsolana\b", r"\bsol\b", r"\bcardano\b", r"\bada\b",
            r"\bxrp\b", r"\bripple\b", r"\bdoge\b", r"dogecoin",
            r"\bbnb\b", r"\bmatic\b", r"\bpolygon\b", r"\bavax\b",
            r"\blink\b", r"chainlink", r"\bshib\b", r"pepe",
            r"\busdt\b", r"\busdc\b", r"stablecoin", r"altcoin",
            # Platforms/Concepts
            r"\bcoinbase\b", r"\bbinance\b", r"\bkraken\b", r"\bftx\b",
            r"\buniswap\b", r"\bopensea\b", r"metamask", r"ledger",
            r"smart contract", r"layer 2", r"\bl2\b", r"rollup",
            r"\bsec\b", r"\bgensler\b", r"spot etf", r"bitcoin etf",
        ],
    },
    
    "science": {
        "keywords": [
            r"\bscience\b", r"scientific", r"research", r"study",
            r"discovery", r"experiment", r"theory", r"hypothesis",
        ],
        "entities": [
            # Fields
            r"\bphysics\b", r"\bchemistry\b", r"\bbiology\b", r"\bastronomy\b",
            r"\bgenetics\b", r"\bneuroscience\b", r"\bclimate\b", r"quantum",
            # Organizations
            r"\bnasa\b", r"\besa\b", r"\bcern\b", r"\bspacex\b",
            r"blue origin", r"\bnoaa\b", r"\bnih\b", r"\bwho\b",
            r"james webb", r"\bjwst\b", r"\bhubble\b",
            # Topics
            r"black hole", r"exoplanet", r"mars", r"moon", r"asteroid",
            r"climate change", r"global warming", r"fusion", r"fission",
            r"vaccine", r"virus", r"\bcrispr\b", r"gene editing",
            r"dark matter", r"dark energy", r"higgs", r"particle",
        ],
    },
}


# =============================================================================
# TIME RANGE EXTRACTION
# =============================================================================

TIME_PATTERNS = {
    "hour": [r"last hour", r"past hour", r"this hour", r"1 hour", r"one hour"],
    "day": [r"\btoday\b", r"last day", r"past day", r"24 hours", r"this day"],
    "week": [r"this week", r"last week", r"past week", r"\bweekly\b", r"7 days"],
    "month": [r"this month", r"last month", r"past month", r"\bmonthly\b", r"30 days"],
    "year": [r"this year", r"last year", r"past year", r"\byearly\b", r"12 months"],
}


def extract_time_range(query: str) -> TimeRange:
    """Extract time range from query, default to 'day'."""
    query_lower = query.lower()
    
    for time_range, patterns in TIME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return time_range
    
    return "day"


# =============================================================================
# TOPIC EXTRACTION (Entity-Aware, Scored)
# =============================================================================

def extract_topic_with_entities(query: str) -> tuple[str, list[str]]:
    """
    Extract topic using both keywords and entity matching.
    Returns (topic, list_of_detected_entities).
    """
    query_lower = query.lower()
    
    # Score each topic
    topic_scores: Dict[str, int] = {}
    topic_entities: Dict[str, list[str]] = {}
    
    for topic, patterns in TOPIC_KEYWORDS.items():
        score = 0
        found_entities = []
        
        # Check keywords (lower weight)
        for kw_pattern in patterns.get("keywords", []):
            if re.search(kw_pattern, query_lower, re.IGNORECASE):
                score += 1
        
        # Check entities (higher weight - entities are more specific)
        for entity_pattern in patterns.get("entities", []):
            match = re.search(entity_pattern, query_lower, re.IGNORECASE)
            if match:
                score += 3  # Entities worth more
                found_entities.append(match.group().lower())
        
        if score > 0:
            topic_scores[topic] = score
            topic_entities[topic] = found_entities
    
    # Return highest scoring topic
    if topic_scores:
        best_topic = max(topic_scores, key=topic_scores.get)
        return best_topic, topic_entities.get(best_topic, [])
    
    # No matches - default to tech
    return "tech", []
# =============================================================================
# ENTITY-SPECIFIC SUBREDDIT OVERRIDES (Comprehensive)
# =============================================================================

ENTITY_SUBREDDIT_OVERRIDES = {
    # --- LLMs / AI Companies & Products ---
    "openai": ["OpenAI", "ChatGPT", "MachineLearning", "artificial"],
    "chatgpt": ["ChatGPT", "OpenAI", "LocalLLaMA", "MachineLearning"],
    "gpt": ["ChatGPT", "OpenAI", "MachineLearning", "LocalLLaMA"],
    "gpt-4": ["ChatGPT", "OpenAI", "MachineLearning"],
    "gpt-4o": ["ChatGPT", "OpenAI", "MachineLearning"],
    "claude": ["ClaudeAI", "artificial", "MachineLearning"],
    "anthropic": ["ClaudeAI", "artificial", "MachineLearning"],
    "gemini": ["Bard", "MachineLearning", "artificial"],
    "google ai": ["Bard", "MachineLearning", "artificial"],
    "meta ai": ["LocalLLaMA", "MachineLearning", "artificial"],
    "llama": ["LocalLLaMA", "MachineLearning", "artificial"],
    "mistral": ["LocalLLaMA", "MachineLearning", "artificial"],
    "deepseek": ["LocalLLaMA", "MachineLearning", "artificial"],
    "perplexity": ["artificial", "MachineLearning", "ChatGPT"],
    "copilot": ["MachineLearning", "programming", "ChatGPT"],
    "stable diffusion": ["StableDiffusion", "MachineLearning", "artificial"],
    "midjourney": ["midjourney", "StableDiffusion", "artificial"],
    "dall-e": ["dalle", "OpenAI", "artificial"],
    "sora": ["OpenAI", "artificial", "MachineLearning"],
    
    # --- LLM Tooling / RAG / Frameworks ---
    "rag": ["LangChain", "LocalLLaMA", "MachineLearning"],
    "vector database": ["MachineLearning", "databases", "LangChain"],
    "langchain": ["LangChain", "LocalLLaMA", "MachineLearning"],
    "llamaindex": ["LangChain", "LocalLLaMA", "MachineLearning"],
    "prompt engineering": ["ChatGPT", "OpenAI", "MachineLearning"],
    "fine-tuning": ["MachineLearning", "LocalLLaMA", "deeplearning"],
    "finetuning": ["MachineLearning", "LocalLLaMA", "deeplearning"],
    "rlhf": ["MachineLearning", "deeplearning", "artificial"],
    "alignment": ["MachineLearning", "artificial", "ControlProblem"],
    "context window": ["LocalLLaMA", "ChatGPT", "MachineLearning"],
    
    # --- ML Frameworks / Research ---
    "pytorch": ["pytorch", "MachineLearning", "deeplearning"],
    "tensorflow": ["tensorflow", "MachineLearning", "deeplearning"],
    "huggingface": ["MachineLearning", "LocalLLaMA", "deeplearning"],
    "hugging face": ["MachineLearning", "LocalLLaMA", "deeplearning"],
    "arxiv": ["MachineLearning", "deeplearning", "artificial"],
    "transformer": ["MachineLearning", "deeplearning", "LocalLLaMA"],
    "neural network": ["MachineLearning", "deeplearning", "learnmachinelearning"],
    "deep learning": ["deeplearning", "MachineLearning", "artificial"],
    "machine learning": ["MachineLearning", "learnmachinelearning", "deeplearning"],
    
    # --- Programming Languages ---
    "python": ["Python", "learnpython", "programming"],
    "javascript": ["javascript", "webdev", "programming"],
    "typescript": ["typescript", "webdev", "programming"],
    "c++": ["cpp", "programming", "learnprogramming"],
    "cpp": ["cpp", "programming", "learnprogramming"],
    "rust": ["rust", "programming"],
    "go": ["golang", "programming"],
    "golang": ["golang", "programming"],
    "java": ["java", "learnjava", "programming"],
    "kotlin": ["Kotlin", "androiddev", "programming"],
    "swift": ["swift", "iOSProgramming", "programming"],
    "c#": ["csharp", "dotnet", "programming"],
    "csharp": ["csharp", "dotnet", "programming"],
    "ruby": ["ruby", "rails", "programming"],
    "php": ["PHP", "webdev", "programming"],
    "scala": ["scala", "programming"],
    "zig": ["Zig", "programming"],
    
    # --- Frameworks / Web Dev ---
    "react": ["reactjs", "webdev", "javascript"],
    "reactjs": ["reactjs", "webdev", "javascript"],
    "next.js": ["nextjs", "webdev", "reactjs"],
    "nextjs": ["nextjs", "webdev", "reactjs"],
    "vue": ["vuejs", "webdev", "javascript"],
    "angular": ["Angular", "webdev", "javascript"],
    "svelte": ["sveltejs", "webdev", "javascript"],
    "fastapi": ["fastapi", "Python", "webdev"],
    "django": ["django", "Python", "webdev"],
    "flask": ["flask", "Python", "webdev"],
    "node.js": ["node", "javascript", "webdev"],
    "nodejs": ["node", "javascript", "webdev"],
    "express": ["node", "javascript", "webdev"],
    
    # --- DevOps / Infrastructure ---
    "docker": ["docker", "devops", "sysadmin"],
    "kubernetes": ["kubernetes", "devops", "sysadmin"],
    "k8s": ["kubernetes", "devops", "sysadmin"],
    "aws": ["aws", "devops", "sysadmin"],
    "azure": ["AZURE", "devops", "sysadmin"],
    "gcp": ["googlecloud", "devops", "sysadmin"],
    "terraform": ["Terraform", "devops", "sysadmin"],
    "ansible": ["ansible", "devops", "sysadmin"],
    "linux": ["linux", "sysadmin", "linuxquestions"],
    "git": ["git", "programming", "learnprogramming"],
    "github": ["github", "programming", "opensource"],
    
    # --- Security ---
    "cybersecurity": ["cybersecurity", "netsec", "AskNetsec"],
    "security": ["netsec", "cybersecurity", "AskNetsec"],
    "infosec": ["netsec", "cybersecurity", "AskNetsec"],
    "malware": ["Malware", "netsec", "cybersecurity"],
    "hacking": ["hacking", "netsec", "cybersecurity"],
    "privacy": ["privacy", "netsec", "PrivacyGuides"],
    "vpn": ["VPN", "privacy", "netsec"],
    
    # --- Hardware / GPUs / PC ---
    "nvidia": ["nvidia", "hardware", "buildapc", "MachineLearning"],
    "amd": ["Amd", "hardware", "buildapc"],
    "intel": ["intel", "hardware", "buildapc"],
    "gpu": ["hardware", "nvidia", "Amd", "MachineLearning"],
    "rtx": ["nvidia", "hardware", "buildapc"],
    "pc build": ["buildapc", "hardware", "pcmasterrace"],
    "build a pc": ["buildapc", "hardware", "pcmasterrace"],
    "laptop": ["laptops", "hardware", "SuggestALaptop"],
    "macbook": ["mac", "apple", "macbook"],
    "iphone": ["iphone", "apple", "ios"],
    "android": ["Android", "androiddev", "GooglePixel"],
    
    # --- Gaming (Platforms & Games) ---
    "gaming": ["gaming", "pcgaming", "Games"],
    "pc gaming": ["pcgaming", "gaming", "buildapc"],
    "steam": ["Steam", "pcgaming", "gaming"],
    "steam deck": ["SteamDeck", "pcgaming", "gaming"],
    "playstation": ["playstation", "PS5", "gaming"],
    "ps5": ["PS5", "playstation", "gaming"],
    "xbox": ["xbox", "xboxone", "gaming"],
    "nintendo": ["nintendo", "NintendoSwitch", "gaming"],
    "switch": ["NintendoSwitch", "nintendo", "gaming"],
    "fortnite": ["FortNiteBR", "FortniteCompetitive", "gaming"],
    "league of legends": ["leagueoflegends", "summonerschool", "gaming"],
    "lol": ["leagueoflegends", "summonerschool", "gaming"],
    "valorant": ["VALORANT", "ValorantCompetitive", "gaming"],
    "cs2": ["GlobalOffensive", "csgo", "pcgaming"],
    "counter-strike": ["GlobalOffensive", "csgo", "pcgaming"],
    "csgo": ["GlobalOffensive", "csgo", "pcgaming"],
    "elden ring": ["Eldenring", "fromsoftware", "gaming"],
    "baldur's gate": ["BaldursGate3", "gaming", "rpg_gamers"],
    "gta": ["GTA", "gtaonline", "gaming"],
    "minecraft": ["Minecraft", "gaming"],
    "zelda": ["zelda", "NintendoSwitch", "gaming"],
    "cod": ["CallOfDuty", "CODWarzone", "gaming"],
    "call of duty": ["CallOfDuty", "CODWarzone", "gaming"],
    "overwatch": ["Overwatch", "gaming", "Competitiveoverwatch"],
    "diablo": ["Diablo", "diablo4", "gaming"],
    "world of warcraft": ["wow", "worldofpvp", "gaming"],
    "wow": ["wow", "worldofpvp", "gaming"],
    "apex legends": ["apexlegends", "gaming", "CompetitiveApex"],
    "destiny": ["DestinyTheGame", "destiny2", "gaming"],
    
    # --- Sports (Generic) ---
    "football": ["soccer", "PremierLeague", "football"],
    "soccer": ["soccer", "PremierLeague", "MLS"],
    "basketball": ["nba", "basketball", "NBAdiscussion"],
    "baseball": ["baseball", "mlb"],
    "hockey": ["hockey", "nhl"],
    "tennis": ["tennis"],
    "golf": ["golf"],
    "cricket": ["Cricket"],
    "rugby": ["rugbyunion"],
    "f1": ["formula1", "F1Technical"],
    "formula 1": ["formula1", "F1Technical"],
    "mma": ["MMA", "ufc"],
    "ufc": ["ufc", "MMA"],
    "boxing": ["Boxing"],
    
    # --- Sports Leagues ---
    "premier league": ["PremierLeague", "soccer", "FantasyPL"],
    "la liga": ["LaLiga", "soccer", "realmadrid"],
    "bundesliga": ["Bundesliga", "soccer", "fcbayern"],
    "champions league": ["ChampionsLeague", "soccer", "football"],
    "ucl": ["ChampionsLeague", "soccer"],
    "serie a": ["SerieA", "soccer", "Juve"],
    "ligue 1": ["Ligue1", "soccer", "psg"],
    "mls": ["MLS", "soccer"],
    "world cup": ["worldcup", "soccer"],
    "euro": ["soccer", "Euro2024"],
    "nba": ["nba", "NBAdiscussion", "basketball"],
    "nfl": ["nfl", "fantasyfootball", "NFLNoobs"],
    "mlb": ["baseball", "mlb"],
    "nhl": ["hockey", "nhl"],
    
    # --- Sports Teams ---
    "manchester united": ["reddevils", "soccer", "PremierLeague"],
    "manchester city": ["MCFC", "soccer", "PremierLeague"],
    "liverpool": ["LiverpoolFC", "soccer", "PremierLeague"],
    "chelsea": ["chelseafc", "soccer", "PremierLeague"],
    "arsenal": ["Gunners", "soccer", "PremierLeague"],
    "tottenham": ["coys", "soccer", "PremierLeague"],
    "real madrid": ["realmadrid", "soccer", "LaLiga"],
    "barcelona": ["Barca", "soccer", "LaLiga"],
    "bayern": ["fcbayern", "soccer", "Bundesliga"],
    "psg": ["psg", "soccer", "Ligue1"],
    "juventus": ["Juve", "soccer", "SerieA"],
    "lakers": ["lakers", "nba", "basketball"],
    "celtics": ["bostonceltics", "nba"],
    "warriors": ["warriors", "nba"],
    
    # --- Athletes ---
    "messi": ["soccer", "Barca", "argentina"],
    "ronaldo": ["soccer", "realmadrid"],
    "mbappe": ["soccer", "realmadrid", "FrenchFootball"],
    "haaland": ["soccer", "MCFC", "PremierLeague"],
    "lebron": ["nba", "lakers"],
    "curry": ["nba", "warriors"],
    "mahomes": ["nfl", "KansasCityChiefs"],
    
    # --- Crypto & Finance ---
    "bitcoin": ["Bitcoin", "CryptoCurrency", "btc"],
    "btc": ["Bitcoin", "CryptoCurrency"],
    "ethereum": ["ethereum", "CryptoCurrency", "ethdev"],
    "eth": ["ethereum", "CryptoCurrency"],
    "solana": ["solana", "CryptoCurrency"],
    "crypto": ["CryptoCurrency", "Bitcoin", "ethereum"],
    "cryptocurrency": ["CryptoCurrency", "Bitcoin", "ethereum"],
    "defi": ["defi", "CryptoCurrency", "ethereum"],
    "nft": ["NFT", "CryptoCurrency"],
    "stocks": ["stocks", "investing", "wallstreetbets"],
    "investing": ["investing", "stocks", "personalfinance"],
    "wallstreetbets": ["wallstreetbets", "stocks"],
    
    # --- News & Politics ---
    "politics": ["politics", "worldnews", "PoliticalDiscussion"],
    "news": ["news", "worldnews", "UpliftingNews"],
    "world news": ["worldnews", "news", "geopolitics"],
    "trump": ["politics", "Conservative", "news"],
    "biden": ["politics", "democrats", "news"],
    "election": ["politics", "PoliticalDiscussion", "news"],
}

# Entity aliases for normalization
ENTITY_ALIASES = {
    "gpt4": "gpt-4",
    "gpt 4": "gpt-4",
    "gpt4o": "gpt-4o",
    "gpt 4o": "gpt-4o",
    "c plus plus": "c++",
    "csharp": "c#",
    "c sharp": "c#",
    "nextjs": "next.js",
    "next js": "next.js",
    "nodejs": "node.js",
    "node js": "node.js",
    "javascript": "javascript",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes",
    "epl": "premier league",
    "prem": "premier league",
    "pl": "premier league",
    "barca": "barcelona",
    "man u": "manchester united",
    "man utd": "manchester united",
    "man city": "manchester city",
    "madrid": "real madrid",
    "bayern munich": "bayern",
    "counter strike": "counter-strike",
    "bg3": "baldur's gate",
    "baldurs gate": "baldur's gate",
    "cod": "call of duty",
    "warzone": "call of duty",
}


def normalize_entity(entity: str) -> str:
    """Normalize entity using aliases."""
    lower = entity.lower().strip()
    return ENTITY_ALIASES.get(lower, lower)


def map_topic_to_subreddits(topic: str, entities: list[str] = None) -> list[str]:
    """
    Map topic to subreddits with entity-specific overrides.
    Supports multiple entities (merge + dedupe with priority).
    Uses hybrid mode: combines targeted subs with topic defaults.
    """
    subreddits = []
    
    # Check for entity-specific overrides first
    if entities:
        for entity in entities:
            normalized = normalize_entity(entity)
            if normalized in ENTITY_SUBREDDIT_OVERRIDES:
                # Add entity-specific subs with high priority
                for sub in ENTITY_SUBREDDIT_OVERRIDES[normalized]:
                    if sub not in subreddits:
                        subreddits.append(sub)
    
    # If we found entity-specific subs, return them (up to 4)
    if subreddits:
        return subreddits[:4]
    
    # Fall back to topic-level mapping
    return TOPIC_SUBREDDIT_MAP.get(topic, TOPIC_SUBREDDIT_MAP.get("tech", []))


# =============================================================================
# INTENT EXTRACTION
# =============================================================================

INTENT_PATTERNS = {
    "highlights": [
        r"\bhighlights?\b", r"key points?", r"main points?", r"tldr", r"tl;?dr",
        r"quick (summary|overview)", r"bullet", r"\bbrief\b", r"top \d+", r"best of"
    ],
    "trending": [
        r"\btrending\b", r"\bhot\b", r"\bbuzz\b", r"\bviral\b", r"popular",
        r"controversial", r"debate", r"drama", r"what.+talking about"
    ],
    "compare": [
        r"which (is |are )?(the )?(best|better|preferred|recommended)",
        r"\bcompare\b", r"\bvs\.?\b", r"\bversus\b", r"difference between",
        r"what do (people|users|redditors) (think|prefer|recommend|say)",
        r"opinion on", r"thoughts on", r"how do people feel"
    ],
    "help": [
        r"^help$", r"how (do|can|to)", r"what (is|are) a?\b", r"\bexplain\b",
        r"commands?$", r"what can you"
    ],
    "settings": [
        r"\bsettings?\b", r"\bpreferences?\b", r"configure", r"setup"
    ],
    "summarize": [
        r"summarize", r"summary", r"what (happened|'s new|'s going on)",
        r"update me", r"tell me about", r"give me", r"show me"
    ]
}


def extract_intent(query: str) -> Intent:
    """Extract the user's intent from the query."""
    query_lower = query.lower()
    
    # Check patterns in priority order
    priority_order = ["compare", "highlights", "trending", "help", "settings", "summarize"]
    
    for intent in priority_order:
        patterns = INTENT_PATTERNS.get(intent, [])
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return intent
    
    return "summarize"


# =============================================================================
# LIMIT EXTRACTION
# =============================================================================

def extract_limit(query: str) -> int:
    """Extract number of posts to fetch from query."""
    patterns = [
        r"(\d+)\s*posts?",
        r"top\s*(\d+)",
        r"show\s*(me\s*)?(\d+)",
        r"(\d+)\s*(results?|items?)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            for group in reversed(match.groups()):
                if group and group.isdigit():
                    n = int(group)
                    if 1 <= n <= 50:
                        return n
    
    return 5


# =============================================================================
# FOLLOW-UP / CORRECTION DETECTION
# =============================================================================

CORRECTION_PATTERNS = [
    # Explicit corrections
    r"(that'?s |)(not what i (asked|meant)|wrong topic)",
    r"i (meant|mean|was asking about|want)",
    r"no[,.]?\s*(i'?m |i was )?(asking|talking) about",
    r"not .+[,.]?\s*(i want|give me|show me)",
    # Topic switches within context
    r"(same (question|thing)|that) (but |)(for|about|on|in)",
    r"(now|instead|actually|rather)\s*(for|about|focus on|show me)",
    r"(change|switch) (it |)(to|the topic to)",
    # Time corrections
    r"(ok|okay|sure|alright)[,.]?\s*(so |now )?(change|switch|try|make it|do)",
    r"(same|that) (but |)(for |about |)(this |last |the |)(week|month|year|day)",
    r"(for |)(this |last |)(week|month|year)( instead)?$",
]


def is_correction_or_refinement(message: str) -> bool:
    """Check if this message is a correction or refinement of previous query."""
    msg_lower = message.lower().strip()
    
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return True
    
    # Very short messages starting with "ok", "no", "not" are likely corrections
    if len(msg_lower.split()) <= 6:
        if re.match(r"^(ok|okay|no|not|actually|i meant|same but)", msg_lower):
            return True
    
    return False


# =============================================================================
# MAIN PARSER
# =============================================================================

def parse_user_query(query: str) -> ParsedQuery:
    """Parse a natural language query and extract all relevant parameters."""
    topic, detected_entities = extract_topic_with_entities(query)
    subreddits = map_topic_to_subreddits(topic, detected_entities)
    time_range = extract_time_range(query)
    intent = extract_intent(query)
    limit = extract_limit(query)
    
    return ParsedQuery(
        topic=topic,
        subreddits=subreddits,
        time_range=time_range,
        intent=intent,
        original_query=query,
        language="en",
        limit=limit,
        detected_entities=detected_entities
    )


# =============================================================================
# MESSAGES
# =============================================================================

def get_greeting_message() -> str:
    """Get a greeting message."""
    return """
## Welcome to Reddit Digest!

I'm here to help you stay updated on what's happening on Reddit!

**What I can do:**
- Summarize what happened today/this week on any topic
- Find the most interesting posts and highlights
- Show what's trending or controversial
- Compare opinions (e.g., "which AI model do people prefer?")

**Topics I know:**
Tech, AI, Programming, Sports, Politics, Gaming, Crypto, Science

**Example questions:**
- "What happened this week in AI?"
- "What's trending in the Premier League today?"
- "Which crypto coins are people talking about?"
- "Give me gaming highlights from this month"
- "What do Redditors think about Python vs JavaScript?"

Just ask me anything!
"""


def get_help_message() -> str:
    """Get a help message."""
    return """
## Help - Reddit Digest

**Commands:**
- `/help` - Show this message
- `/topics` - Show available topics
- `/settings` - View preferences
- `/weekly on/off` - Toggle weekly digest
- `/reset` - Clear conversation context
- `/quit` - Exit

**Tips:**
- I understand team names (Lakers, Real Madrid), game titles (Elden Ring), crypto coins (Solana), AI models (Claude, GPT-4), and more.
- Specify time: "today", "this week", "this month"
- Ask for highlights: "give me the highlights"
- Ask for trending: "what's hot", "what's controversial"
- If I get the topic wrong, just say "I meant [topic]" and I'll correct it.

**Examples:**
- "What's the buzz around Baldur's Gate 3?"
- "Bitcoin news this week"
- "Champions League highlights"
"""
