from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import ChannelAccount
from typing import List
import httpx
import openai
import asyncio
from utils.http_manager import make_get_request, make_post_request
from config import DefaultConfig
import datetime

CONFIG = DefaultConfig()

openai.api_key = CONFIG.openai_api_key

async def get_result_background_task(url, turn_context):
    try:
        response = await make_get_request(url)
        print(response)
        if response.status_code == 200:
            response_data = response.json()
            await explain_code_answer(turn_context, response_data[0]['student_code'], response_data[1]['closest_code'],  response_data[2]['question'])
        else:
            await turn_context.send_activity("Failed to get result.")
    except httpx.HTTPError:
        await turn_context.send_activity("An error occurred while getting the result.")



from utils.prompts import create_prompt
async def explain_code_answer(turn_context: TurnContext, student_code, closest_code, question):
    
    messages= create_prompt(question, student_code, closest_code)
        
    prompt = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": messages}
    ]

    # Send user prompt to OpenAI and get a response
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=prompt,
        max_tokens=1500,  # Adjust the max tokens limit as needed
        temperature=0.5  # Adjust the temperature for more or less randomness
    )

    answer = response.choices[0].message.content

    await turn_context.send_activity(MessageFactory.text(f"{answer}"))

class EchoBot(ActivityHandler):
    def __init__(self):
        self.user_sessions = {}

    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")

########### Main entry point of any message flow ###########
    async def on_message_activity(self, turn_context: TurnContext):
        user_id = turn_context.activity.from_property.id

        # Create new session if the user has no session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'is_expecting_attachments': False,
                'awaiting_input': False,
                'student_id': None,
                'question_no': None,
                'module_code': None,
                'get_result': False,
                'chat_history': [],
                'code_help': [],
                'is_waiting_for_code_help': False,
                'awaiting_user_code': False,
                'question_solved': False
            }

        session = self.user_sessions[user_id]

        # Determine which message flow depends on the user's activity
        if session['is_expecting_attachments']:
            await self.handle_attachments(turn_context, session)
            session['is_expecting_attachments'] = False
        elif session['awaiting_input']:
            await self.handle_input(turn_context, session)
        elif turn_context.activity.text == "/submit":
            session['awaiting_input'] = True
            await self.handle_submit_command(turn_context, session)
        elif turn_context.activity.text == "/result":
            session['awaiting_input'] = True
            await self.handle_result_command(turn_context, session)
        elif turn_context.activity.attachments:
            await self.handle_unexpected_attachment(turn_context)
        elif turn_context.activity.text == "/code_help":
            await turn_context.send_activity("Sure, please provide the coding problem you need help with.")
            session['is_waiting_for_code_help'] = True
        elif session['is_waiting_for_code_help']:
            await self.handle_code_help_request(turn_context, session)
        elif session['awaiting_user_code']:
            await self.handle_user_code(turn_context, session)      
        else:
            await self.handle_text_message(turn_context, session)

    async def handle_invalid_submission(self, turn_context: TurnContext):
        await turn_context.send_activity("Invalid submission. Please upload a file.")

    async def handle_unexpected_attachment(self, turn_context: TurnContext):
        await turn_context.send_activity("Unexpected attachment. Please type /submit first.")

    async def handle_code_help_request(self, turn_context: TurnContext, session):
        user_prompt = turn_context.activity.text
        hint_only_prompt = ". Do not give me direct answer, give me some hints instead."

        session['is_waiting_for_code_help'] = False
        session['code_help'].append({"role": "user", "content": user_prompt + hint_only_prompt})

        # Include the entire chat history in the prompt, including the user's input
        prompt = session['code_help']

        # Send user prompt to OpenAI and get a response
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=prompt,
            max_tokens=1500,  # Adjust the max tokens limit as needed
            temperature=0.5  # Adjust the temperature for more or less randomness
        )

        # Extract the generated answer from the response
        answer = response.choices[0].message.content

        # Append OpenAI's response to the chat history
        session['code_help'].append({"role": "assistant", "content": answer})

        await turn_context.send_activity(MessageFactory.text(f"{answer}"))
        await turn_context.send_activity(MessageFactory.text("Now, let me see your answer!"))
        session['awaiting_user_code'] = True


    async def handle_user_code(self, turn_context: TurnContext, session):
        user_prompt = turn_context.activity.text
        session['code_help'].append({"role": "user", "content": user_prompt + " . If my answer solves the problem, praise me. Else, give me the hint to correct the code and explain why my code is wrong."})
        prompt = session['code_help']

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=prompt,
            max_tokens=1500,  # Adjust the max tokens limit as needed
            temperature=0.5  # Adjust the temperature for more or less randomness
        )

        # Extract the generated answer from the response
        answer = response.choices[0].message.content

        # Append OpenAI's response to the chat history
        session['code_help'].append({"role": "assistant", "content": answer})

        await turn_context.send_activity(MessageFactory.text(f"{answer}"))        
    
        # Reset the awaiting_input flag
        session['awaiting_user_code'] = False


    async def handle_text_message(self, turn_context: TurnContext, session):

        user_prompt = turn_context.activity.text

        session['chat_history'].append({"role": "user", "content": user_prompt})
        prompt = session['chat_history']
        
        # Send user prompt to OpenAI and get a response
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=prompt,
            max_tokens=1500,  # Adjust the max tokens limit as needed
            temperature=0.5  # Adjust the temperature for more or less randomness
        )
        # Extract the generated answer from the response
        answer = response.choices[0].message.content

        session['chat_history'].append({"role": "assistant", "content": answer})

        await turn_context.send_activity(MessageFactory.text(f"{answer}"))


    async def handle_input(self, turn_context: TurnContext, session):
        user_id = turn_context.activity.from_property.id
        user_input = turn_context.activity.text

        if session['student_id'] is None:
            session['student_id'] = user_input
            await turn_context.send_activity("Please provide the module code.")
        elif session['module_code'] is None:
            session['module_code'] = user_input
            await turn_context.send_activity("Please provide the question number.")
        elif session['question_no'] is None:
            session['question_no'] = user_input
            session['awaiting_input'] = False
            if session['get_result']:
                await self.handle_get_result(turn_context, session)
                session['get_result'] = False
            else:
                await turn_context.send_activity("Thank you for the input. Now, please upload the file.")
                session['is_expecting_attachments'] = True
        else:
            await turn_context.send_activity("Invalid input. Please try again.")
            session['student_id'] = None
            session['question_no'] = None
            session['module_code'] = None
            session['awaiting_input'] = False

    async def handle_submit_command(self, turn_context: TurnContext, session):
        session['awaiting_input'] = True
        await turn_context.send_activity("Please provide the student ID.")

    async def handle_attachments(self, turn_context: TurnContext, session):
        if turn_context.activity.attachments:
            for attachment in turn_context.activity.attachments:
                # Handle attachments
                await self.handle_file_attachment(turn_context, attachment, session)
        else:
            session['student_id'] = None
            session['question_no'] = None
            await self.handle_invalid_submission(turn_context)

    async def handle_file_attachment(self, turn_context: TurnContext, attachment, session):
        if attachment.content_type == 'text/x-python':
            content_url = attachment.content_url
            try:
                payload = {
                    'question_no': session['question_no'],
                    'student_id': session['student_id'],
                    'module_code': session['module_code'],
                    'python_code': content_url
                }
    
                response = await make_post_request(
                    f"api/submit_answer_file",
                    payload
                )
                if response.status_code == 200:
                    await turn_context.send_activity("File submitted successfully.")
                else:
                    print(response.text)
                    print(response.status_code)
                    await turn_context.send_activity("Failed to submit the file.")
            except httpx.HTTPError:
                await turn_context.send_activity("An error occurred while submitting the file.")
            finally:
                session['student_id'] = None
                session['question_no'] = None
                session['module_code'] = None
        else:
            session['student_id'] = None
            session['question_no'] = None
            session['module_code'] = None
            await turn_context.send_activity("Invalid file format. Please upload a Python file.")

    async def handle_result_command(self, turn_context: TurnContext, session):
        session['awaiting_input'] = True
        session['get_result'] = True
        await turn_context.send_activity("Please provide the student ID.")

    async def handle_get_result(self, turn_context: TurnContext, session):

        # year to be changed
        current_year = datetime.datetime.now().year
        query_params = {
            'question_no': str(session['question_no']),
            'student_id': str(session['student_id']),
            'module_code': session['module_code'],
            'year': '2018'
        }
        query_string = "&".join(f"{key}={value}" for key, value in query_params.items())
        url = f"api/calculate_distance?{query_string}"
        
        asyncio.create_task(get_result_background_task(url, turn_context))

        session['student_id'] = None
        session['question_no'] = None
        session['module_code'] = None
        await turn_context.send_activity("Thank you for the input. Please wait for the result.")

    
