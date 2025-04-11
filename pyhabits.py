import json
import csv
import os
import webbrowser
from datetime import datetime, timedelta
import pdfkit

# Folder structure
USER_FOLDER = "user"
EXPORTS_FOLDER = "exports"
HABIT_FILE = os.path.join(USER_FOLDER, "habits.json")
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ======================
# Core Functions
# ======================

def ensure_user_folder_exists():
    """Ensure the 'user' folder exists."""
    if not os.path.exists(USER_FOLDER):
        os.makedirs(USER_FOLDER)

def ensure_exports_folder_exists():
    """Ensure the exports folder structure exists."""
    if not os.path.exists(EXPORTS_FOLDER):
        os.makedirs(EXPORTS_FOLDER)
    
    current_year = datetime.now().strftime("%Y")
    year_folder = os.path.join(EXPORTS_FOLDER, current_year)
    if not os.path.exists(year_folder):
        os.makedirs(year_folder)
    
    return year_folder

def get_visualization_folder():
    """Get the visualization folder path with date structure."""
    year_folder = ensure_exports_folder_exists()
    date_folder = datetime.now().strftime("%d-%m-%Y")
    vis_folder = os.path.join(year_folder, date_folder)
    
    if not os.path.exists(vis_folder):
        os.makedirs(vis_folder)
    
    return vis_folder

def load_habits():
    """Load habits from the JSON file."""
    ensure_user_folder_exists()
    if os.path.exists(HABIT_FILE):
        with open(HABIT_FILE, "r") as file:
            return json.load(file)
    return {}

def save_habits(habits):
    """Save habits to the JSON file."""
    ensure_user_folder_exists()
    with open(HABIT_FILE, "w") as file:
        json.dump(habits, file, indent=4)

def get_current_date():
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

def get_current_day():
    """Get today's day of the week."""
    return datetime.now().strftime("%A")

def get_current_week():
    """Get the current week's start and end dates."""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")

def get_current_month():
    """Get the current month's start and end dates."""
    today = datetime.now()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d")

# ======================
# Habit Tracking Functions
# ======================

def track_habit(habits):
    """Track a habit for the current day."""
    if habits:
        print("\nYour saved habits:")
        for habit, data in habits.items():
            measurement = data.get("measurement")
            if measurement:
                print(f"- {habit} (Measurement: {measurement})")
            else:
                print(f"- {habit}")
    else:
        print("\nNo habits saved yet.")

    habit_name = input("\nEnter the habit name (or a new one to add): ").strip()
    today_date = get_current_date()
    today_day = get_current_day()

    if habit_name in habits:
        if habits[habit_name]["completion"].get(today_date, False):
            print(f"'{habit_name}' already tracked today.")
            return
    else:
        measurement = input(f"Enter the measurement for '{habit_name}' (e.g., '15 pages', '30 min', '2 km') or press Enter to skip: ").strip()
        habits[habit_name] = {
            "measurement": measurement if measurement else None,
            "completion": {}
        }

    habits[habit_name]["completion"][today_date] = True
    print(f"'{habit_name}' marked as completed for {today_day}, {today_date}.")
    save_habits(habits)

# ======================
# Viewing and Export Functions
# ======================

def view_habits(habits, period="today"):
    """View habits for today, this week, or this month."""
    if not habits:
        print("No habits found to display.")
        return

    today_date = get_current_date()
    today_day = get_current_day()
    start_of_week, end_of_week = get_current_week()
    start_of_month, end_of_month = get_current_month()

    if period == "today":
        print(f"\nHabits for {today_day}, {today_date}:")
        for habit, data in habits.items():
            completed = data["completion"].get(today_date, False)
            status = "✓" if completed else "✗"
            measurement = data.get("measurement")
            if measurement:
                print(f"- {habit} (Measurement: {measurement}): {status}")
            else:
                print(f"- {habit}: {status}")
    elif period == "week":
        print(f"\nHabits for the week {start_of_week} to {end_of_week}:")
        for habit, data in habits.items():
            print(f"\nHabit: {habit}")
            if data.get("measurement"):
                print(f"Measurement: {data['measurement']}")
            for day in DAYS_OF_WEEK:
                date = (datetime.strptime(start_of_week, "%Y-%m-%d") + timedelta(days=DAYS_OF_WEEK.index(day))).strftime("%Y-%m-%d")
                completed = data["completion"].get(date, False)
                status = "✓" if completed else "✗"
                print(f"  {day}, {date}: {status}")
    elif period == "month":
        print(f"\nHabits for the month {start_of_month} to {end_of_month}:")
        current_date = datetime.strptime(start_of_month, "%Y-%m-%d")
        end_date = datetime.strptime(end_of_month, "%Y-%m-%d")

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            day_str = current_date.strftime("%A")
            print(f"\n{day_str}, {date_str}:")
            for habit, data in habits.items():
                completed = data["completion"].get(date_str, False)
                status = "✓" if completed else "✗"
                measurement = data.get("measurement")
                if measurement:
                    print(f"- {habit} (Measurement: {measurement}): {status}")
                else:
                    print(f"- {habit}: {status}")
            current_date += timedelta(days=1)

    if period in ["week", "month"]:
        export_habits(habits, period, start_of_week if period == "week" else start_of_month, 
                     end_of_week if period == "week" else end_of_month)

def export_habits(habits, period, start_date, end_date):
    """Export habits to JSON, CSV, or Markdown."""
    ensure_exports_folder_exists()
    while True:
        print("\nExport Options:")
        print("1. Export as JSON")
        print("2. Export as CSV")
        print("3. Export as Markdown")
        print("4. Exit")
        choice = input("Choose an option (1/2/3/4): ").strip()

        if choice == "1":
            filename = os.path.join(EXPORTS_FOLDER, f"habits_{period}_{start_date}_to_{end_date}.json")
            try:
                with open(filename, "w") as file:
                    json.dump(habits, file, indent=4)
                print(f"Habits exported to {filename}")
            except Exception as e:
                print(f"Error exporting to JSON: {e}")
        elif choice == "2":
            filename = os.path.join(EXPORTS_FOLDER, f"habits_{period}_{start_date}_to_{end_date}.csv")
            try:
                with open(filename, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Habit", "Measurement", "Date", "Status"])
                    for habit, data in habits.items():
                        for date, completed in data["completion"].items():
                            writer.writerow([habit, data.get("measurement", ""), date, "✓" if completed else "✗"])
                print(f"Habits exported to {filename}")
            except Exception as e:
                print(f"Error exporting to CSV: {e}")
        elif choice == "3":
            filename = os.path.join(EXPORTS_FOLDER, f"habits_{period}_{start_date}_to_{end_date}.md")
            try:
                with open(filename, "w") as file:
                    file.write(f"# Habits for {period} ({start_date} to {end_date})\n\n")
                    for habit, data in habits.items():
                        file.write(f"## {habit}\n")
                        if data.get("measurement"):
                            file.write(f"- **Measurement**: {data['measurement']}\n")
                        file.write("| Date       | Status |\n")
                        file.write("|------------|--------|\n")
                        for date, completed in data["completion"].items():
                            file.write(f"| {date} | {'✓' if completed else '✗'} |\n")
                        file.write("\n")
                print(f"Habits exported to {filename}")
            except Exception as e:
                print(f"Error exporting to Markdown: {e}")
        elif choice == "4":
            break
        else:
            print("Invalid choice. Please try again.")

# ======================
# Visualization Functions
# ======================

def generate_visualization(habits):
    """Generate HTML and PDF visualizations with organized folder structure"""
    if not habits:
        print("No habits found to visualize.")
        return

    # Ask user what to visualize
    print("\nGenerate visualization for:")
    print("1. All habits")
    print("2. Specific habit")
    choice = input("Choose an option (1/2): ").strip()

    if choice == "2":
        # Show available habits
        print("\nAvailable habits:")
        for i, habit in enumerate(habits.keys(), 1):
            print(f"{i}. {habit}")
        
        # Get user selection
        while True:
            try:
                habit_choice = input("\nEnter the number of the habit to visualize (or 'cancel' to go back): ").strip()
                if habit_choice.lower() == 'cancel':
                    return
                
                habit_index = int(habit_choice) - 1
                selected_habit = list(habits.keys())[habit_index]
                generate_single_visualization(habits, selected_habit)
                break
            except (ValueError, IndexError):
                print("Invalid selection. Please enter a valid number or 'cancel'.")
    elif choice == "1":
        # Generate all visualizations
        vis_folder = get_visualization_folder()
        print(f"\nGenerating visualizations for all habits in: {vis_folder}")
        for habit in habits:
            generate_single_visualization(habits, habit)
    else:
        print("Invalid choice. Returning to main menu.")

def generate_single_visualization(habits, habit_name):
    """Generate visualization for a single habit"""
    if habit_name not in habits:
        print(f"Habit '{habit_name}' not found.")
        return

    vis_folder = get_visualization_folder()
    data = habits[habit_name]
    current_year = datetime.now().year
    
    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Habit Tracker - {habit_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .year {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .month {{ width: 200px; margin-bottom: 30px; break-inside: avoid; }}
        .month-name {{ font-weight: bold; text-align: center; margin-bottom: 10px; }}
        .calendar {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }}
        .day {{ height: 20px; text-align: center; border: 1px solid #ddd; font-size: 10px; }}
        .completed {{ background-color: #4CAF50; color: white; }}
        .empty {{ background-color: #f9f9f9; }}
        @page {{ size: A4; margin: 10mm; }}
        @media print {{ 
            body {{ margin: 0; padding: 0; }}
            .month {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div style="page-break-after: always;">
        <h1>{habit_name}{f' ({data["measurement"]})' if data.get("measurement") else ''}</h1>
        <div class="year">"""
    
    # Add months
    for month in range(1, 13):
        month_name = datetime.strptime(f"{month}", "%m").strftime("%B")
        html_content += f"""
        <div class="month">
            <div class="month-name">{month_name} {current_year}</div>
            <div class="calendar">"""
        
        # Add days
        for day in range(1, 32):
            try:
                date_str = f"{current_year}-{month:02d}-{day:02d}"
                if date_str in data["completion"]:
                    html_content += f'<div class="day completed" title="{date_str}">{day}</div>'
                else:
                    html_content += f'<div class="day empty" title="{date_str}">{day}</div>'
            except ValueError:
                pass
        
        html_content += """
            </div>
        </div>"""
    
    html_content += """
        </div>
    </div>
</body>
</html>"""
    
    # Save files
    safe_habit_name = "".join(c for c in habit_name if c.isalnum() or c in " _-")
    html_filename = os.path.join(vis_folder, f"habit_{safe_habit_name}_visualization.html")
    pdf_filename = os.path.join(vis_folder, f"habit_{safe_habit_name}_visualization.pdf")
    
    try:
        # Save HTML
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Generate PDF
        options = {
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
            'encoding': "UTF-8",
            'quiet': ''
        }
        pdfkit.from_string(html_content, pdf_filename, options=options)
        
        print(f"\nGenerated visualization for '{habit_name}'")
        print(f"HTML: {html_filename}")
        print(f"PDF: {pdf_filename}")
        
        # Open in browser
        webbrowser.open(f"file://{os.path.abspath(html_filename)}")
    except Exception as e:
        print(f"\nError generating visualization for '{habit_name}': {e}")
        if "No wkhtmltopdf executable found" in str(e):
            print("Please install wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html")

# ======================
# Main Application
# ======================

def main():
    # Check wkhtmltopdf installation
    try:
        pdfkit.from_string("<html><body><h1>Test</h1></body></html>", "test.pdf")
        os.remove("test.pdf")
    except Exception as e:
        print("\nWarning: PDF generation might not work properly.")
        print(f"Error: {str(e)}")
        print("Please ensure wkhtmltopdf is installed from: https://wkhtmltopdf.org/downloads.html\n")

    habits = load_habits()

    while True:
        print("\nHabit Tracker")
        print("1. Track a habit for today")
        print("2. View habits for today")
        print("3. View habits for this week")
        print("4. View habits for this month")
        print("5. Generate visualization (HTML/PDF)")
        print("6. Exit")
        choice = input("Choose an option (1/2/3/4/5/6): ").strip()

        if choice == "1":
            track_habit(habits)
        elif choice == "2":
            view_habits(habits, period="today")
        elif choice == "3":
            view_habits(habits, period="week")
        elif choice == "4":
            view_habits(habits, period="month")
        elif choice == "5":
            generate_visualization(habits)
        elif choice == "6":
            print("Exiting the Habit Tracker. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()