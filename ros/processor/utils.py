import ast as type_evaluation


def validate_type(value, type_):
    """
    Validate the type of a value.
    Currently available types: bool
    :param value: Value to validate.
    :param type_: Type to validate against.
    :return: True if the value is of the specified type, False otherwise.
    """
    if type_ == bool:
        # ast.literal_eval does not understand lowercase 'True' or 'False'
        value = value.capitalize() if value in ['true', 'false'] else value
    evaluated_value = type_evaluation.literal_eval(value) if value else None

    return True if type(evaluated_value) == type_ else False
