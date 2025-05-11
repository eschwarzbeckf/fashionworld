from fastapi import APIRouter
from fastapi import HTTPException, status
from validations import ModelandText, SupplierProducts
import ollama

router = APIRouter(
    prefix="/api/llm"
)

ollama_client = ollama.Client(host="http://localhost:11434")

@router.post("/read_email", status_code=status.HTTP_200_OK)
async def read_email(model_and_text: ModelandText):
    """
    """
    model_name = model_and_text.model_name
    text = model_and_text.text

    prompt = f"""
        You are an AI assistant tasked with extracting structured data from emails sent by textile providers. 
        Read the following email content carefully and extract the relevant information about the textile products mentioned. 
        Format the extracted information strictly as a JSON object according to the structure provided below.

        Look for the supplier name, garment type, material, size, collection, weight, and weight units.
        The supplier name is mentioned either at the signature of the email or at the beginning of the email, or in the subject line.
        The email may contain information about multiple garments, and you should extract details for each garment separately.
        The garments may include jackets, shorts, sweaters, skirts, shirts, t-shirts, coats, pants, dresses, suits, blouses, and hoodies.
        The materials may include cotton, polyester, silk, linen, wool, and denim.
        The sizes may include s, m, l, x, and xxl.
        The collections may include summer, winter, fall, and spring.
        The weight may be mentioned in grams or other units, and you should extract the weight value and its unit.

        If there is any null value set the null_values to true.
        If all the information can be extracted set the null_values to false.

        **Desired JSON Structure:**
        ```json
        {{
            "supplier": "Supplier Name from Email",
            "data":[{{
                "garment_type": "extracted garment type",
                "material": "extracted material",
                "size": "extracted size or null",
                "collection": "extracted collection or null",
                "weight_units": "extracted weight units or 'kg'",
                "weight": extracted weight (number)
            }},
            "null_values": false
            // ... repeat for each garment mentioned in the email
            ]
        }}

        --- START OF EMAIL CONTENT ---
        {text}
        --- END OF EMAIL CONTENT ---
    """
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name is required.")
    
    if text:
        messages = [{"role":"system","content": "You are a helpful assistant."}, {"role": "user", "content": prompt}]
        response = ollama_client.chat(
            model=model_name, 
            messages=messages,
            stream=False,
            format=SupplierProducts.model_json_schema(),
            options={
                "temperature":0.0
                }
            )
        return response
    else:
        raise HTTPException(status_code=400, detail="Text is required.")
