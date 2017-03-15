import datetime
import sqlalchemy
import sqlalchemy.ext.declarative
import utils
from sqlalchemy.orm import scoped_session
from sqlalchemy import asc
from sqlalchemy import Column
from sqlalchemy import desc
from sqlalchemy import Integer
from sqlalchemy import String


Base = sqlalchemy.ext.declarative.declarative_base()
_sessions = {}


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    review = Column(Integer)
    commit_date = Column(Integer)
    process_date = Column(Integer)
    osp_release = Column(String)
    status = Column(String)


class Package(Base):
    __tablename__ = "packages"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    version = Column(String)
    release_date = Column(Integer)
    process_date = Column(Integer)
    review_number = Column(Integer)
    osp_release = Column(String)
    status = Column(String)
    retries = Column(Integer)


def get_reviews(session, review=None, status=None, without_status=None,
                osp_release=None, limit=100, order="asc", since=None,
                before=None):
    reviews = session.query(Review)
    if review is not None:
        reviews = reviews.filter(Review.review == review)
    if status is not None:
        reviews = reviews.filter(Review.status == status)
    if without_status is not None:
        reviews = reviews.filter(Review.status != without_status)
    if osp_release is not None:
        reviews = reviews.filter(Review.osp_release == osp_release)
    if since is not None:
        reviews = reviews.filter(Review.commit_date > since)
    if before is not None:
        reviews = reviews.filter(Review.commit_date < before)
    order_by = asc
    if order == "desc":
        order_by = desc
    reviews = reviews.order_by(order_by(Review.review))
    if limit:
        reviews = reviews.limit(limit)
    return reviews.all()


def get_packages(session, review=None, status=None, without_status=None,
                 osp_release=None, name=None, order="asc", since=None,
                 before=None):
    packages = session.query(Package)
    if review is not None:
        packages = packages.filter(Package.review_number == review)
    if status is not None:
        packages = packages.filter(Package.status == status)
    if without_status is not None:
        packages = packages.filter(Package.status != without_status)
    if osp_release is not None:
        packages = packages.filter(Package.osp_release == osp_release)
    if since is not None:
        packages = packages.filter(Package.release_date > since)
    if before is not None:
        packages = packages.filter(Package.release_date < before)
    order_by = asc
    if order == "desc":
        order_by = desc
    packages = packages.order_by(order_by(Package.release_date))
    return packages.all()


def add_review(session, review, osp_release=None):
    rel_date = utils.review_time_fmt(review['submitted'])
    process_date = datetime.datetime.now().strftime("%s")
    review_obj = Review(review=review['_number'],
                        status='PROCESSED',
                        osp_release=osp_release,
                        commit_date=rel_date,
                        process_date=process_date)
    session.add(review_obj)
    session.commit()


def add_package(session, pkg, status='NEW'):
    process_date = datetime.datetime.now().strftime("%s")
    pkg.process_date = process_date
    pkg.status = status
    session.add(pkg)
    session.commit()


def update_status(session, obj, status):
    process_date = datetime.datetime.now().strftime("%s")
    obj.status = status
    obj.process_date = process_date
    session.add(obj)
    session.commit()


def get_session(url='sqlite://', new=False):
    if _sessions.get(url) and new is False:
        return _sessions.get(url)

    engine = sqlalchemy.create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    _sessions[url] = scoped_session(sqlalchemy.orm.sessionmaker(bind=engine))
    return _sessions[url]
