def create_prompt(question, my_answer, closest_code):
    file_path = "prompts.txt"
    prompt_name = "Main"
    try:
        with open(file_path, "r") as file:
            content = file.read()
            prompt_start = content.find(f"<{prompt_name}>")
            if prompt_start != -1:
                prompt_end = content.find(f"<{prompt_name}>", prompt_start + len(f"<{prompt_name}>"))
                if prompt_end != -1:
                    prompt_text = content[prompt_start + len(f"<{prompt_name}>"):prompt_end].strip()
                    updated_message = prompt_text.replace("{question}", question)
                    updated_message = updated_message.replace("{my_answer}", my_answer)
                    updated_message = updated_message.replace("{closest_code}", closest_code)

                    return updated_message
                else:
                    print(f"Ending tag not found for '{prompt_name}'.")
            else:
                print(f"Prompt '{prompt_name}' not found in the file.")
                return None
            
    except FileNotFoundError:
        print("File not found: prompts.txt")
        return None
    except IOError as e:
        print(f"Error reading the file: {e}")
        return None