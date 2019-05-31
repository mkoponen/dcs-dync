# Common functions needed by several classes, such that don't depend on any other class except constants.

import constants


def version_string_to_number(version_str):

    # We convert version numbers into a single number that is then easy to properly compare. Our scheme requires
    # that none of the four numbers are higher than 99.
    str_split = version_str.split(".")

    # 1.0.0.0-post3 -type version names are allowed, but a hyphen may only occur in the very last number.
    if "-" in str_split[-1]:
        post_split = str_split[-1].split("-")
        # For calculating compatibility, we ignore the post. Any -postX version may never break compatibility, or
        # it must actually increment a number if it would.
        str_split[-1] = post_split[0]
    len_split = len(str_split)
    for i in range(4):
        if i < len_split:
            try:
                str_split[i] = int(str_split[i])
            except ValueError:
                return None
            if str_split[i] >= 100:
                return None
        else:
            str_split.append(0)
    ver_num = 0
    multiplier = 1
    for i in range(4):
        ver_num += multiplier * str_split[3 - i]
        multiplier *= 100
    return ver_num


def get_version_numbers():

    app_num = version_string_to_number(constants.app_version)
    if app_num is None:
        return None, None

    comp_num = version_string_to_number(constants.backwards_compatibility_min_version)
    if comp_num is None:
        return None, None

    return app_num, comp_num
