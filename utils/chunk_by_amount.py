# from stackoverflow? can't find
def chunk_by_amount(lst, n_chunks):
    avg = len(lst) / float(n_chunks)
    out = []
    last = 0.0

    while last < len(lst):
        out.append(lst[int(last):int(last + avg)])
        last += avg

    if len(lst) < n_chunks:
        out = [e for e in out if e]

    return out