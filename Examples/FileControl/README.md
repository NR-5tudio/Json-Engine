# Scene Description:
This scene shows how json engine check, make, and read a file

# Timeline:
### 1. **does_MyFile_exist.json (First Attempt)**
- **Code:**
```json
{
    "begin":
    [
        {"print": "$(does_file_exist ['My File.txt'])"},

        {
            "if": 
            [
                "$(does_file_exist ['My File.txt'])",
                {
                    "true": "Yes",
                    "false": "No"
                }
            ]
        }
    ],

    
    "Yes": 
    [
        {
            "print": "Yes, the file does exists"
        }
    ],

    "No": 
    [
        {
            "print": "No, the file doesn't exists"
        }
    ]
}
```
print if the file `My File.txt` exists (True/False)
**If True**: Call the function 'Yes' -> prints "Yes, the file does exists"
**If False**: Call the function 'No' -> prints "No, the file doesn't exists"
- **Output:** `False` - The file does not exist

### 2. **make_MyFile.json**
- **Code:**
```json
{
    "begin": 
    [
        {
            "write_string_to_file": 
            [
                "My File.txt",
                "Hello from json!"
            ]
        }
    ]
}
```
- **Action:** Creates the file (no output shown)

### 3. **does_MyFile_exist.json (Second Attempt) **
- **Code:** (same as the above but 'Yes' instead)
- **Output:** `True` - The file now exists

### 4. **Read File Contents**
- **Code:**
```json
{
    "begin": 
    [
        {
            "print": "$(read_file ['My File.txt'])"
        }
    ]
}
```
- **Output:** `Hello from json!` - Successfully reads the file content