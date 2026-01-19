def calculate_sm2(rating, ease_factor, interval, repetitions):
    """Standard SM-2 Algorithm implementation.
    Returns (new_ease_factor, new_interval, new_repetitions)
    """
    # SM-2 expects rating 0-5. Ensure minimum of 0 and max of 5.
    rating = max(0, min(rating, 5))

    # If quality rating < 3, reset repetitions and interval
    if rating < 3:
        repetitions = 0
        interval = 1
    else:
        # Update repetitions
        repetitions += 1

        # Calculate new interval based on repetitions
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = round(interval * ease_factor)

    # Update ease factor
    ease_factor = ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    # Minimum ease factor is 1.3
    if ease_factor < 1.3:
        ease_factor = 1.3

    return ease_factor, interval, repetitions
