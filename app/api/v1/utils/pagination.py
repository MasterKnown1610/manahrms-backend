"""
Global pagination utility for querying with filters, sorting, and pagination.
Can be used across all services in the application.
"""
from typing import List, Tuple, Optional, Any, Type
from sqlalchemy.orm import Query
from sqlalchemy import Column, desc, asc, and_, or_, func
from sqlalchemy.sql import expression

from app.api.v1.schemas.common import (
    PaginationRequest,
    PaginationInfo,
    PaginatedResponse,
    FilterCondition,
    SortCondition,
    FilterOperator,
    SortOrder
)


def apply_filters(query: Query, filters: Optional[List[FilterCondition]], model: Type) -> Query:
    """
    Apply filter conditions to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        filters: List of filter conditions
        model: SQLAlchemy model class
    
    Returns:
        Query with filters applied
    """
    if not filters:
        return query
    
    filter_conditions = []
    
    for filter_cond in filters:
        field_name = filter_cond.field
        operator = filter_cond.operator
        value = filter_cond.value
        
        # Get the column from the model
        if not hasattr(model, field_name):
            # Skip invalid fields
            continue
        
        column: Column = getattr(model, field_name)
        
        # Apply filter based on operator
        if operator == FilterOperator.EQUALS:
            filter_conditions.append(column == value)
        elif operator == FilterOperator.NOT_EQUALS:
            filter_conditions.append(column != value)
        elif operator == FilterOperator.GREATER_THAN:
            filter_conditions.append(column > value)
        elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            filter_conditions.append(column >= value)
        elif operator == FilterOperator.LESS_THAN:
            filter_conditions.append(column < value)
        elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
            filter_conditions.append(column <= value)
        elif operator == FilterOperator.CONTAINS:
            # For string fields, use ILIKE for case-insensitive search
            filter_conditions.append(column.ilike(f"%{value}%"))
        elif operator == FilterOperator.IN:
            if isinstance(value, list):
                filter_conditions.append(column.in_(value))
        elif operator == FilterOperator.NOT_IN:
            if isinstance(value, list):
                filter_conditions.append(~column.in_(value))
        elif operator == FilterOperator.IS_NULL:
            filter_conditions.append(column.is_(None))
        elif operator == FilterOperator.IS_NOT_NULL:
            filter_conditions.append(column.isnot(None))
    
    if filter_conditions:
        query = query.filter(and_(*filter_conditions))
    
    return query


def apply_sorting(query: Query, sort_conditions: Optional[List[SortCondition]], model: Type) -> Query:
    """
    Apply sort conditions to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        sort_conditions: List of sort conditions
        model: SQLAlchemy model class
    
    Returns:
        Query with sorting applied
    """
    if not sort_conditions:
        return query
    
    for sort_cond in sort_conditions:
        field_name = sort_cond.field
        order = sort_cond.order
        
        # Get the column from the model
        if not hasattr(model, field_name):
            # Skip invalid fields
            continue
        
        column: Column = getattr(model, field_name)
        
        if order == SortOrder.DESC:
            query = query.order_by(desc(column))
        else:
            query = query.order_by(asc(column))
    
    return query


def paginate_query(
    query: Query,
    pagination_request: PaginationRequest,
    model: Type
) -> Tuple[List[Any], PaginationInfo]:
    """
    Apply pagination, filters, and sorting to a query and return results.
    
    Args:
        query: SQLAlchemy query object
        pagination_request: Pagination request with filters, sort, and pagination
        model: SQLAlchemy model class
    
    Returns:
        Tuple of (items list, pagination info)
    """
    # Apply filters
    query = apply_filters(query, pagination_request.filter, model)
    
    # Get total count before pagination
    total_items = query.count()
    
    # Apply sorting
    query = apply_sorting(query, pagination_request.sort, model)
    
    # Apply pagination
    page = pagination_request.page
    page_size = pagination_request.page_size
    offset = (page - 1) * page_size
    
    items = query.offset(offset).limit(page_size).all()
    
    # Calculate pagination metadata
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    has_next = page < total_pages
    has_previous = page > 1
    
    pagination_info = PaginationInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous
    )
    
    return items, pagination_info


def create_paginated_response(
    items: List[Any],
    pagination_info: PaginationInfo,
    response_model: Type
) -> PaginatedResponse:
    """
    Create a paginated response from items and pagination info.
    
    Args:
        items: List of items to include in response
        pagination_info: Pagination metadata
        response_model: Pydantic model for response items
    
    Returns:
        PaginatedResponse object
    """
    # Convert items to response models
    data = [response_model.model_validate(item) for item in items]
    
    return PaginatedResponse[response_model](
        data=data,
        pagination=pagination_info
    )

