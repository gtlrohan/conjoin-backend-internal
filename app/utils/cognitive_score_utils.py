from app.postgres.models.card import CompletionLevel, HowWasIt


def calculate_score_impact(how_was_it: HowWasIt, completion_level: CompletionLevel) -> float:
    # Define base values for how_was_it
    how_was_it_values = {
        HowWasIt.terrible: -1,
        HowWasIt.bad: -0.5,
        HowWasIt.ok: 0.2,
        HowWasIt.good: 0.5,
        HowWasIt.awesome: 1,
    }

    # Define additional multipliers for completion_level
    completion_level_multipliers = {
        CompletionLevel.partly: 0.5,
        CompletionLevel.fully: 1.0,
        CompletionLevel.incomplete: -1.0,
    }

    cognitive_score = how_was_it_values[how_was_it]

    if completion_level == CompletionLevel.incomplete:
        cognitive_score = -1

    if completion_level == CompletionLevel.partly:
        if cognitive_score >= 0:
            cognitive_score *= completion_level_multipliers[completion_level]
        else:
            cognitive_score -= completion_level_multipliers[completion_level] * 0.5
            cognitive_score = min(abs(cognitive_score), 1) * -1  # make sure cog_score can't go less then 1

    return cognitive_score
