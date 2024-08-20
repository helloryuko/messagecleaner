from itertools import islice

# ref: https://stackoverflow.com/a/22045226
def chunk_by_size(lst, n_size):
    it = iter(lst)
    return iter(lambda: tuple(islice(it, n_size)), ())