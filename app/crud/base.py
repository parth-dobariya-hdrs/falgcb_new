# ================================
# FILE: app/crud/base.py
# ================================

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalars().first()

    async def get_multi(
            self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())  # Convert Sequence to List to match return type

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
            self,
            db: AsyncSession,
            *,
            db_obj: ModelType,
            obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        obj = result.scalars().first()
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

# # ================================
# # FILE: app/crud/base.py
# # ================================

# from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
# from fastapi.encoders import jsonable_encoder
# from pydantic import BaseModel
# from sqlalchemy.orm import Session

# ModelType = TypeVar("ModelType")
# CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
# UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

# class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
#     def __init__(self, model: Type[ModelType]):
#         """
#         CRUD object with default methods to Create, Read, Update, Delete (CRUD).
#         **Parameters**
#         * `model`: A SQLAlchemy model class
#         * `schema`: A Pydantic model (schema) class
#         """
#         self.model = model

#     async def get(self, db: Session, id: Any) -> Optional[ModelType]:
#         return db.query(self.model).filter(self.model.id == id).first()

#     async def get_multi(
#         self, db: Session, *, skip: int = 0, limit: int = 100
#     ) -> List[ModelType]:
#         return db.query(self.model).offset(skip).limit(limit).all()

#     async def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
#         obj_in_data = jsonable_encoder(obj_in)
#         db_obj = self.model(**obj_in_data)
#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj

#     async def update(
#         self,
#         db: Session,
#         *,
#         db_obj: ModelType,
#         obj_in: Union[UpdateSchemaType, Dict[str, Any]]
#     ) -> ModelType:
#         obj_data = jsonable_encoder(db_obj)
#         if isinstance(obj_in, dict):
#             update_data = obj_in
#         else:
#             update_data = obj_in.dict(exclude_unset=True)

#         for field in obj_data:
#             if field in update_data:
#                 setattr(db_obj, field, update_data[field])

#         db.add(db_obj)
#         db.commit()
#         db.refresh(db_obj)
#         return db_obj

#     async def remove(self, db: Session, *, id: int) -> ModelType:
#         obj = db.query(self.model).get(id)
#         db.delete(obj)
#         db.commit()
#         return obj
