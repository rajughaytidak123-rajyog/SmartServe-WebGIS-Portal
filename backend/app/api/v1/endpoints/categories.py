from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.session import get_db
from backend.app.schemas.category import CategoryResponse, CategorySummary, SubcategoryDetail

router = APIRouter()

@router.get(
    "/",
    response_model=List[CategoryResponse],
    summary="List All Categories & Subcategories",
    description="Retrieve all 20 service categories with icons, colors, slugs, and live POI counts."
)
def get_categories(db: Session = Depends(get_db)):
    query_sql = """
        SELECT 
            c.id,
            c.category,
            c.subcategory,
            c.slug,
            c.icon,
            c.color,
            COUNT(s.id) AS count
        FROM categories c
        LEFT JOIN services s ON c.subcategory = s.subcategory
        GROUP BY c.id, c.category, c.subcategory, c.slug, c.icon, c.color
        ORDER BY c.category ASC, c.subcategory ASC;
    """
    rows = db.execute(text(query_sql)).fetchall()
    return [
        CategoryResponse(
            id=r.id,
            category=r.category,
            subcategory=r.subcategory,
            slug=r.slug,
            icon=r.icon,
            color=r.color,
            count=int(r.count)
        )
        for r in rows
    ]

@router.get(
    "/tree",
    response_model=List[CategorySummary],
    summary="Hierarchical Category Tree",
    description="Get nested hierarchy of categories and their respective subcategories for dynamic UI navigation."
)
def get_category_tree(db: Session = Depends(get_db)):
    query_sql = """
        SELECT 
            c.id,
            c.category,
            c.subcategory,
            c.slug,
            c.icon,
            c.color,
            COUNT(s.id) AS count
        FROM categories c
        LEFT JOIN services s ON c.subcategory = s.subcategory
        GROUP BY c.id, c.category, c.subcategory, c.slug, c.icon, c.color
        ORDER BY c.category ASC, c.subcategory ASC;
    """
    rows = db.execute(text(query_sql)).fetchall()

    tree_dict = {}
    for r in rows:
        cat_name = r.category
        if cat_name not in tree_dict:
            tree_dict[cat_name] = {
                "category": cat_name,
                "icon": r.icon,
                "color": r.color,
                "total_count": 0,
                "subcategories": []
            }

        subcat_count = int(r.count)
        tree_dict[cat_name]["total_count"] += subcat_count
        tree_dict[cat_name]["subcategories"].append(
            SubcategoryDetail(
                id=r.id,
                subcategory=r.subcategory,
                slug=r.slug,
                icon=r.icon,
                color=r.color,
                count=subcat_count
            )
        )

    return list(tree_dict.values())
