from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import structlog

logger = structlog.get_logger()

def clean_phone_number(phone: str) -> str:
    """
    Clean and standardize phone number
    
    Args:
        phone (str): Phone number to clean
    Returns:
        str: Cleaned phone number
    examples:
        "03482423267" -> "+923482423267"
        "+92-348-2423267" -> "+923482423267"
    """
    digits = re.sub(r'\D', '' ,phone)

    if digits.startswith("0"):
        digits = "92" + digits[1:]
    elif not digits.startswith("92"):
        digits = "92" + digits
    
    return "+" + digits

def extract_number_from_text(text: str) -> List[int]:
    """
    Extract all numbers form text

    Args:
        text: Input text
    Returns:
        List of int found in text
    Examples:
        "I am 25 years old" -> [25]
        "Call 0300-1234567" -> [300, 1234567]
    """
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]

def get_severity_from_scale(scale: int) -> str:
    """
    Convert numeric pain scale to severity level
    
    Args:
        scale: Pain scale (1-10)
    
    Returns:
        Severity level: mild, moderate, severe
    
    Examples:
        get_severity_from_scale(3) -> "mild"
        get_severity_from_scale(7) -> "severe"
    """
    if scale <= 3:
        return "mild"
    elif scale <= 6:
        return "moderate"
    else:
        return "severe"

def get_time_of_day() -> str:
    """
    Get current time of day
    
    Returns:
        morning, afternoon, evening, or night
    """
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour <= 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"

def get_greetings(language: str = "urdu") -> str:
    """
    Get time-appropriate greeting
    
    Args:
        language: Language code (urdu/english)
    
    Returns:
        Greeting message
    """
    time_of_day = get_time_of_day()
    greetings = {
        "urdu": {
            "morning": "صبح بخیر",
            "afternoon": "سلام",
            "evening": "شام بخیر",
            "night": "شب بخیر"
        },
        "english": {
            "morning": "Good morning",
            "afternoon": "Good afternoon",
            "evening": "Good evening",
            "night": "Good night"
        }
    }

    return greetings.get(language, greetings["urdu"]).get(time_of_day, "السلام علیکم")

def truncated_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].strip() + suffix

def parse_duration(text: str) -> Optional[str]:
    """
    Parse duration from user text
    
    Args:
        text: User input text
    
    Returns:
        Standardized duration string or None
    
    Examples:
        "2 ghante se" -> "2 hours"
        "3 din se" -> "3 days"
        "kal se" -> "since yesterday"
    """
    text_lower = text.lower()

    numbers = extract_number_from_text(text)

    patterns = {
        r'(\d+)\s*(ghante|hours|hour|ghanta)': lambda n: f"{n} hours",
        r'(\d+)\s*(din|days|day)': lambda n: f"{n} days",
        r'(\d+)\s*(hafte|weeks|week|hafta)': lambda n: f"{n} weeks",
        r'(\d+)\s*(mahine|months|month|mahina)': lambda n: f"{n} months",
        r'(abhi|just now|right now)': lambda _: "just now",
        r'(aaj|today)': lambda _: "today",
        r'(kal|yesterday)': lambda _: "since yesterday",
    }
    for pattern, formatter in patterns.items():
        match = re.search(pattern, text_lower)
        if match:
            if numbers:
                return formatter(numbers[0])
            else:
                return formatter(None)

    return None

def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_cnic(cnic: str) -> bool:
    """
    Validate Pakistani CNIC format
    
    Args:
        cnic: CNIC number
    
    Returns:
        True if valid, False otherwise
    
    Examples:
        "42101-1234567-1" -> True
        "4210112345671" -> True
        "12345" -> False
    """
    cnic_digits = re.sub(r'\D', '', cnic)

    return len(cnic_digits) == 13 and cnic_digits.isdigit()

def format_cnic(cnic: str) -> str:
    """
    Format CNIC with dashes
    
    Args:
        cnic: CNIC number (with or without dashes)
    
    Returns:
        Formatted CNIC (XXXXX-XXXXXXX-X)
    
    Examples:
        "4210112345671" -> "42101-1234567-1"
    """
    digits = re.sub(r'\D', '', cnic)
    
    if len(digits) != 13:
        return cnic
    
    return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"

def get_day_name(language: str = "english") -> str:
    """
    Get current day name
    
    Args:
        language: Language (english/urdu)
    
    Returns:
        Day name in specified language
    """
    day = datetime.now().strftime("%A")

    day_names = {
        "urdu": {
            "Monday": "پیر",
            "Tuesday": "منگل",
            "Wednesday": "بدھ",
            "Thursday": "جمعرات",
            "Friday": "جمعہ",
            "Saturday": "ہفتہ",
            "Sunday": "اتوار"
        },
        "english": {
            "Monday": "Monday",
            "Tuesday": "Tuesday",
            "Wednesday": "Wednesday",
            "Thursday": "Thursday",
            "Friday": "Friday",
            "Saturday": "Saturday",
            "Sunday": "Sunday"
        }
    }

    return day_names.get(language, day_names["english"]).get(day, day)

def sanitize_user_input(text: str) -> str:
    """
    Sanitize user input for security
    
    Args:
        text: User input
    
    Returns:
        Sanitized text
    """
    text = re.sub(r'[<>\"\'`]', '', text)
    return text

def is_working_hours(branch_timings: Dict[str, str]) -> bool:
    """
    Check if current time is within working hours
    
    Args:
        branch_timings: Branch timing dict
    
    Returns:
        True if within working hours, False otherwise
    """
    try:
        now = datetime.now()
        day = now.strftime("%A").lower()

        timing = branch_timings.get(day.lower())

        if not timing or timing.lower() == "closed":
            return False

        if "-" in timing:
            start_str, end_str = timing.split("-")
            start_time = datetime.strptime(start_str.strip(), "%I:%M %p").time()
            end_time = datetime.strptime(end_str.strip(), "%I:%M %p").time()

            current_time = now.time()
            return start_time <= current_time <= end_time

        return False
    except Exception as e:
        logger.error(f"working_hours_check_failed", error=str(e))
        return False

def calculate_age_from_year(birth_year: int) -> int:
    """
    Calculate age from birth year
    
    Args:
        birth_year: Year of birth
    
    Returns:
        Age in years
    """
    current_year = datetime.now().year
    return current_year - birth_year

def format_list_urdu(items: List[str]) -> str:
    """
    Format list in Urdu with proper conjunction
    
    Args:
        items: List of items
    
    Returns:
        Formatted string
    
    Examples:
        ["احمد", "علی"] -> "احمد اور علی"
        ["احمد", "علی", "حسن"] -> "احمد، علی اور حسن"
    """

    if not items:
        return ""
    
    if len(items) ==1:
        return items[0]
    
    if len(items) ==2:
        return f"{items[0]} اور {items[1]}"
    
    return "، ".join(items[:-1]) + f" اور {items[-1]}"

def format_list_english(items: List[str]) -> str:
    """
    Format list in English with proper conjunction
    
    Args:
        items: List of items
    
    Returns:
        Formatted string
    
    Examples:
        ["Ahmed", "Ali"] -> "Ahmed and Ali"
        ["Ahmed", "Ali", "Hassan"] -> "Ahmed, Ali and Hassan"
    """

    if not items:
        return ""
    
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    
    return ", ".join(items[:-1]) + f" and {items[-1]}"

def is_emergency_time() -> bool:
    """
    Check if it's after normal working hours (emergency time)
    
    Returns:
        True if after 10 PM or before 8 AM
    """

    hour = datetime.now().hour
    return hour >= 22 or hour < 8

def get_next_working_day() -> str:
    """
    Get next working day (excluding Sunday if needed)
    
    Returns:
        Day name
    """

    tomorrow = datetime.now()

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_day_index = tomorrow.weekday()
    next_day_index = (current_day_index + 1) % 7

    return days[next_day_index]