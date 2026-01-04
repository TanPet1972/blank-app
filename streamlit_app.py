import datetime as dt
import io
import zipfile

from PIL import Image, ExifTags
import streamlit as st

DATE_FORMAT = "%d-%m-%Y"
NO_DATE_FOLDER = "Sans_date"

EXIF_TAGS = {value: key for key, value in ExifTags.TAGS.items()}
DATE_TAGS = [
    EXIF_TAGS.get("DateTimeOriginal"),
    EXIF_TAGS.get("DateTimeDigitized"),
    EXIF_TAGS.get("DateTime"),
]


def parse_exif_date(image: Image.Image) -> dt.date | None:
    exif_data = image.getexif()
    if not exif_data:
        return None

    for tag in DATE_TAGS:
        if tag is None:
            continue
        raw_value = exif_data.get(tag)
        if not raw_value:
            continue
        try:
            return dt.datetime.strptime(raw_value, "%Y:%m:%d %H:%M:%S").date()
        except ValueError:
            continue
    return None


def build_zip(files: list[tuple[str, bytes]]) -> tuple[bytes, dict[str, int]]:
    stats: dict[str, int] = {}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, data in files:
            file_date = None
            try:
                with Image.open(io.BytesIO(data)) as image:
                    file_date = parse_exif_date(image)
            except OSError:
                file_date = None

            if file_date:
                folder_name = file_date.strftime(DATE_FORMAT)
            else:
                folder_name = NO_DATE_FOLDER

            stats[folder_name] = stats.get(folder_name, 0) + 1
            archive_path = f"{folder_name}/{filename}"
            archive.writestr(archive_path, data)

    return buffer.getvalue(), stats


st.set_page_config(page_title="Tri de photos", page_icon="📸")

st.title("📸 Tri automatique de photos")
st.write(
    "Chargez vos photos et récupérez une archive ZIP avec des dossiers par date de prise. "
    "Le format utilisé est **jour-mois-année** (ex. 27-03-2024)."
)

uploaded_files = st.file_uploader(
    "Ajoutez des photos (JPEG, PNG, HEIC si pris en charge)",
    type=["jpg", "jpeg", "png", "heic"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.info("Nous analysons les métadonnées EXIF pour déterminer la date de prise.")
    files_payload = [(file.name, file.getvalue()) for file in uploaded_files]
    zip_bytes, zip_stats = build_zip(files_payload)

    st.subheader("Résumé")
    for folder, count in sorted(zip_stats.items()):
        st.write(f"- **{folder}** : {count} photo(s)")

    st.download_button(
        "Télécharger l'archive ZIP",
        data=zip_bytes,
        file_name="photos_triees.zip",
        mime="application/zip",
    )
else:
    st.warning("Ajoutez des photos pour lancer le tri.")
