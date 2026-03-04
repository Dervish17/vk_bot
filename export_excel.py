import pandas as pd
from database.database import Data


def export_excel(filename="certificates.xlsx"):
    rows = get_all_users()

    df = pd.DataFrame(
        rows,
        columns=["ФИО", "VK ID", "Кол-во получений", "Последняя дата"]
    )

    df.to_excel(filename, index=False)
    return filename
