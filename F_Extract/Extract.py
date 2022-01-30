

def get_most_common_values_from_list_or_set(values: list or set, num_of_return_values: int):
    return sorted(values, key=values.count, reverse=True)[:num_of_return_values]