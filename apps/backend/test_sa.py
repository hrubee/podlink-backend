import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)

async def test():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(User(name="u1"))
    db.commit()
    
    # Test IN with string
    res = db.query(User).filter(User.id.in_(["1"])).all()
    print("SQLAlchemy IN with string array:", [u.name for u in res])
    
asyncio.run(test())
