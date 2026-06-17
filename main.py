from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import pulp
import json

import models
from database import engine, get_db

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="School Meals Scheduler")

# Endpoint to populate/add an ingredient to the system
@app.post("/ingredients/")
def create_ingredient(name: str, cost: float, calories: float, protein: float, stock: float, db: Session = Depends(get_db)):
    db_ingredient = models.Ingredient(
        name=name.lower(), cost_per_kg=cost, 
        calories_per_kg=calories, protein_per_kg=protein, stock_kg=stock
    )
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    return {"message": f"Successfully added {name} to inventory!", "data": db_ingredient}

# Optimized Generator that reads from DB and writes back history
@app.post("/generate-and-save-menu/")
def generate_and_save_menu(date: str, students: int, budget_per_student: float, db: Session = Depends(get_db)):
    # 1. Fetch live ingredient profiles from SQLite database
    ingredients = db.query(models.Ingredient).all()
    if not ingredients:
        raise HTTPException(status_code=400, detail="Database is empty. Please add ingredients first.")

    # 2. Setup baseline mathematical limits
    total_budget = students * budget_per_student
    min_calories = students * 800
    min_protein = students * 30

    prob = pulp.LpProblem("DB_School_Meal_Optimization", pulp.LpMinimize)

    # 3. Decision Variables mapped dynamically to DB entries
    vars_dict = {}
    for ing in ingredients:
        # Prevent selecting more than what is physically stocked in inventory
        vars_dict[ing.name] = pulp.LpVariable(f"kg_{ing.name}", lowBound=0, upBound=ing.stock_kg, cat='Continuous')

    # 4. Objective & Constraints
    prob += pulp.lpSum([vars_dict[ing.name] * ing.cost_per_kg for ing in ingredients]), "Total_Cost"
    prob += pulp.lpSum([vars_dict[ing.name] * ing.calories_per_kg for ing in ingredients]) >= min_calories, "Calories"
    prob += pulp.lpSum([vars_dict[ing.name] * ing.protein_per_kg for ing in ingredients]) >= min_protein, "Protein"
    prob += pulp.lpSum([vars_dict[ing.name] * ing.cost_per_kg for ing in ingredients]) <= total_budget, "Budget"

    # 5. Solve optimization matrix
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise HTTPException(status_code=422, detail="Infeasible allocation! Either stock is too low or budget constraints are impossible to satisfy.")

    # 6. Parse shopping recipe list
    shopping_list = {ing.name: round(vars_dict[ing.name].varValue, 2) for ing in ingredients if vars_dict[ing.name].varValue > 0}
    final_cost = pulp.value(prob.objective)

    # 7. Persist calculated schedule event into database record history
    new_schedule = models.SavedSchedule(
        date=date,
        students_fed=students,
        total_cost=round(final_cost, 2),
        menu_json=json.dumps(shopping_list)
    )
    db.add(new_schedule)
    db.commit()

    return {
        "status": "Schedule successfully optimized and saved to database!",
        "date": date,
        "total_cost_kes": round(final_cost, 2),
        "allocated_recipe": shopping_list
    }

