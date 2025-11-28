""" """

from star_foundry import MongoStarRepository, StarRegistry


class StarLoader:
    """
    Loads and registers Star entities from a data source.
    """

    def __init__(self, repository: MongoStarRepository, registry: StarRegistry):
        """
        Initialize the StarLoader with a repository and registry.

        Args:
            repository: The MongoStarRepository instance to load Stars from
            registry: The StarRegistry instance to register loaded Stars into
        """
        self.repository = repository
        self.registry = registry

    def load_all(self):
        """
        Load all Stars from the repository and register them in the registry.
        """
        stars = self.repository.find_all()
        for star in stars:
            self.registry.register(star)
        self.registry.finalize()
