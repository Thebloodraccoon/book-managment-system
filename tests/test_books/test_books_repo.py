from app.books.repository import AuthorRepository, BookRepository


class TestBookRepository:
    def test_get_by_id_with_author(self, db_session, test_book):
        repo = BookRepository(db_session)

        book = repo.get_by_id_with_author(test_book.id)

        assert book is not None
        assert book.id == test_book.id
        assert hasattr(book, "author")
        assert book.author.name == test_book.author.name

    def test_get_by_id_with_author_not_found(self, db_session):
        repo = BookRepository(db_session)

        book = repo.get_by_id_with_author(99999)

        assert book is None


class TestAuthorRepository:
    def test_get_by_name(self, db_session, test_author):
        repo = AuthorRepository(db_session)

        author = repo.get_by_name(test_author.name)

        assert author is not None
        assert author.name.lower() == test_author.name.lower()

    def test_get_by_name_case_insensitive(self, db_session, test_author):
        repo = AuthorRepository(db_session)

        author = repo.get_by_name(test_author.name.upper())

        assert author is not None
        assert author.name == test_author.name

    def test_get_by_name_not_found(self, db_session):
        repo = AuthorRepository(db_session)

        author = repo.get_by_name("Nonexistent Author")

        assert author is None
