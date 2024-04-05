from django.core.exceptions import ValidationError


def check_if_only_contains_numbers(proportions_string):
    try:
        return list(map(int, proportions_string.split(':')))
    except ValueError:
        raise ValidationError(f'{proportions_string} does not contain only numbers!')


def check_if_sum_is_hundred(proportions_list):
    epsilon = 1
    # TODO: maybe check not of mod 10 rest 0
    if sum(proportions_list) % 10 != 0:
        if (sum(proportions_list) + epsilon) % 10 != 0:
            raise ValidationError(f'{proportions_list} does not give 100%')


def validate_proportions(proportions_string):
    if ':' not in proportions_string:
        raise ValidationError(f'Only parent proportions found, please define atleast one child proportion in {proportions_string} separated through ":"')
    if '_' in proportions_string:
        test = proportions_string.split('_')
        child_proportions = [test[i] for i in range(len(test)) if test[i].count(':') > 0]
        parent_proportions = [test[i] for i in range(len(test)) if test[i].count(':') == 0]
        for child in child_proportions:
            child_proportions_list = check_if_only_contains_numbers(child)
            check_if_sum_is_hundred(child_proportions_list)
        parent_proportions_list = check_if_only_contains_numbers(':'.join(parent_proportions))
        check_if_sum_is_hundred(parent_proportions_list)
    else:
        try:
            proportions = list(map(int, proportions_string.split(':')))
        except ValueError:
            raise ValidationError(f'{proportions_string} does not contain only numbers!')
        check_if_sum_is_hundred(proportions)


def round_c_rates(c_rates):
    rounded_c_rates = []
    for c_rate in c_rates:
        resolution = 0.05
        if c_rate is not None:
            rounded_c_rates.append(round(round(c_rate/resolution)*resolution, 2))
    return list(set(rounded_c_rates))
