from sqlalchemy.orm import Session

from .auth import hash_password
from .models import Category, CustomFieldDef, Project, SampleObject, User

DEFAULT_CATEGORIES = [
    ("WB", "#F56C6C", 1),
    ("PCR", "#409EFF", 2),
    ("统计数据", "#67C23A", 3),
    ("病理图片", "#E6A23C", 4),
    ("其他", "#909399", 9),
]

DEFAULT_FIELDS = {
    "WB": [
        {"label": "抗体", "field_type": "select", "select_options": ["anti-GAPDH", "anti-β-actin", "anti-Tubulin", "其他"],
         "is_required": False, "sort_order": 1},
        {"label": "曝光时间", "field_type": "text", "is_required": False, "sort_order": 2},
    ],
    "PCR": [
        {"label": "引物对", "field_type": "text", "is_required": False, "sort_order": 1},
        {"label": "Ct均值", "field_type": "number", "is_required": False, "sort_order": 2},
    ],
    "病理图片": [
        {"label": "染色方法", "field_type": "select", "select_options": ["HE", "Masson", "免疫组化", "免疫荧光"],
         "is_required": False, "sort_order": 1},
        {"label": "放大倍数", "field_type": "select", "select_options": ["40x", "100x", "200x", "400x"],
         "is_required": False, "sort_order": 2},
    ],
}

DEFAULT_OBJECTS = [
    ("HEK293", "cell", "HEK293T, 293T"),
    ("C57BL/6小鼠", "animal", "C57, C57BL6"),
    ("小鼠心脏组织", "tissue", "heart, 心肌"),
]


def seed(db: Session) -> None:
    if db.query(User).count() == 0:
        db.add(User(username="admin", password_hash=hash_password("admin123"),
                    display_name="管理员", role="admin"))
    if db.query(Project).count() == 0:
        db.add(Project(code="ProjectA", name="示例项目A", description="可编辑或删除"))
        db.add(Project(code="ProjectB", name="示例项目B", description=""))
    if db.query(Category).count() == 0:
        cat_by_name = {}
        for name, color, order in DEFAULT_CATEGORIES:
            cat = Category(name=name, color=color, sort_order=order)
            db.add(cat)
            cat_by_name[name] = cat
        db.flush()  # 先拿到自增 id，再挂自定义字段
        for cat_name, fields in DEFAULT_FIELDS.items():
            cat = cat_by_name.get(cat_name)
            if cat is None:
                continue
            for f in fields:
                db.add(CustomFieldDef(category_id=cat.id, field_key=f["label"], label=f["label"],
                                      field_type=f["field_type"],
                                      select_options=f.get("select_options"),
                                      is_required=f.get("is_required", False),
                                      sort_order=f.get("sort_order", 0)))
    if db.query(SampleObject).count() == 0:
        for name, kind, aliases in DEFAULT_OBJECTS:
            db.add(SampleObject(name=name, kind=kind, aliases=aliases))
    db.commit()
