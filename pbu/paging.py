class PagingInformation:
    """
    Data structure to store paging information. The first page is page 0
    """

    def __init__(self, page=0, page_size=25):
        """
        Creates a new object with the provided parameters.
        """
        self.page = page
        self.page_size = page_size
