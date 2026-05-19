# import sql model and session
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime

Base = declarative_base()

class Brief(Base):
    __tablename__ = 'briefs'

    id = Column(Integer, primary_key=True)
    brief_text = Column(Text, nullable=False)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    brief_id = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)
    event_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    brief_id = Column(Integer, nullable=False)
    source_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///webpilot.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

