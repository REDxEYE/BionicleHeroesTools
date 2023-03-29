from typing import List


def unstripify(indices_strip: List[int]):
    indices = []
    for i in range(2, len(indices_strip)):
        if i % 2 == 0:
            v0 = indices_strip[i - 2]
            v1 = indices_strip[i - 1]
            v2 = indices_strip[i]
        else:
            v0 = indices_strip[i]
            v1 = indices_strip[i - 1]
            v2 = indices_strip[i - 2]
        if v0 == v1 or v1 == v2:
            continue
        indices.append((v0, v1, v2))
    return indices
