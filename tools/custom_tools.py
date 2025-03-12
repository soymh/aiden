import os
import requests
import subprocess
from datetime import datetime
from tools.base_tool import ToolBase


class CustomTools(ToolBase):
    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """
        print(__user__)
        result = ""
        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"
        if result == "":
            result = "User: Unknown"
        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a human-readable format.
        :return: The current time.
        """
        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # 12-hour format with AM/PM
        current_date = now.strftime("%A, %B %d, %Y")
        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(self, equation: str) -> str:
        """
        Calculate the result of an equation.
        :param equation: The equation to calculate.
        """
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(self, city: str) -> str:
        """
        Get the current weather for a given city.
        :param city: The name of the city to get the weather for.
        :return: The current weather information or an error message.
        """
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": api_key, "units": "metric"}
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"
            temperature = data["main"]["temp"]
            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"

    def run_shell_command(self, command: str) -> dict:
        """
        Execute a shell command on the local machine after obtaining user confirmation.
        
        :param command: Shell command to be executed.
        :return: A dictionary with keys "status" (and if successful, "stdout", "stderr", and "returncode").
        """
        print(f"Shell Command Execution Request: {command}")
        user_confirm = input("Do you want to execute this shell command? (yes/no): ").strip().lower()
        if user_confirm not in ["yes", "y"]:
            return {"status": "aborted", "message": "Command execution aborted by user."}
        
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return {
                "status": "success",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
