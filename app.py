import os

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    url_for
)


# Load the variables stored in the .env file
load_dotenv()

# Create the Flask application
app = Flask(__name__)


def get_database_connection():
    """Create and return a connection to the MySQL database."""

    return mysql.connector.connect(
        host="127.0.0.1",
        port=int(os.getenv("MYSQL_PORT", "3307")),
        database=os.getenv("MYSQL_DATABASE"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD")
    )


@app.route("/")
def polling_unit_results():
    """Display the results of a selected polling unit."""

    selected_polling_unit_id = request.args.get(
        "polling_unit_id",
        type=int
    )

    connection = get_database_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            uniqueid,
            polling_unit_number,
            polling_unit_name
        FROM polling_unit
        ORDER BY polling_unit_name, polling_unit_number
        """
    )

    polling_units = cursor.fetchall()
    selected_polling_unit = None
    results = []

    if selected_polling_unit_id is not None:
        cursor.execute(
            """
            SELECT
                uniqueid,
                polling_unit_number,
                polling_unit_name
            FROM polling_unit
            WHERE uniqueid = %s
            """,
            (selected_polling_unit_id,)
        )

        selected_polling_unit = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                party_abbreviation,
                party_score
            FROM announced_pu_results
            WHERE polling_unit_uniqueid = %s
            ORDER BY party_abbreviation
            """,
            (str(selected_polling_unit_id),)
        )

        results = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "index.html",
        polling_units=polling_units,
        selected_polling_unit=selected_polling_unit,
        results=results
    )


@app.route("/lga-results")
def lga_results():
    """Display summed polling unit results for a selected LGA."""

    selected_lga_id = request.args.get("lga_id", type=int)

    connection = get_database_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            lga_id,
            lga_name
        FROM lga
        WHERE state_id = 25
        ORDER BY lga_name
        """
    )

    lgas = cursor.fetchall()
    selected_lga = None
    results = []

    if selected_lga_id is not None:
        cursor.execute(
            """
            SELECT
                lga_id,
                lga_name
            FROM lga
            WHERE lga_id = %s
              AND state_id = 25
            """,
            (selected_lga_id,)
        )

        selected_lga = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                result.party_abbreviation,
                SUM(result.party_score) AS total_score
            FROM announced_pu_results AS result
            INNER JOIN polling_unit AS polling
                ON result.polling_unit_uniqueid = polling.uniqueid
            WHERE polling.lga_id = %s
            GROUP BY result.party_abbreviation
            ORDER BY total_score DESC
            """,
            (selected_lga_id,)
        )

        results = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "lga_results.html",
        lgas=lgas,
        selected_lga=selected_lga,
        results=results
    )


@app.route("/wards/<int:lga_id>")
def wards_by_lga(lga_id):
    """Return the wards belonging to a selected LGA."""

    connection = get_database_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            uniqueid,
            ward_id,
            ward_name
        FROM ward
        WHERE lga_id = %s
        ORDER BY ward_name
        """,
        (lga_id,)
    )

    wards = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(wards)


@app.route(
    "/new-polling-unit",
    methods=["GET", "POST"]
)
def new_polling_unit():
    """Store a new polling unit and results for all parties."""

    connection = get_database_connection()
    cursor = connection.cursor(dictionary=True)

    # Load the Delta State local governments
    cursor.execute(
        """
        SELECT
            lga_id,
            lga_name
        FROM lga
        WHERE state_id = 25
        ORDER BY lga_name
        """
    )

    lgas = cursor.fetchall()

    # LABOUR is stored as LABO in the polling unit result table
    cursor.execute(
        """
        SELECT
            CASE
                WHEN partyid = 'LABOUR' THEN 'LABO'
                ELSE partyid
            END AS party_abbreviation,
            partyname
        FROM party
        ORDER BY id
        """
    )

    parties = cursor.fetchall()

    created_polling_unit_id = request.args.get(
        "created",
        type=int
    )

    error_message = None
    redirect_polling_unit_id = None

    if request.method == "POST":
        try:
            lga_id = int(request.form.get("lga_id", ""))
            ward_uniqueid = int(
                request.form.get("ward_uniqueid", "")
            )

            polling_unit_number = request.form.get(
                "polling_unit_number",
                ""
            ).strip()

            polling_unit_name = request.form.get(
                "polling_unit_name",
                ""
            ).strip()

            polling_unit_description = request.form.get(
                "polling_unit_description",
                ""
            ).strip()

            entered_by_user = request.form.get(
                "entered_by_user",
                ""
            ).strip()

            if not polling_unit_number:
                raise ValueError(
                    "The polling unit number is required."
                )

            if not polling_unit_name:
                raise ValueError(
                    "The polling unit name is required."
                )

            if not entered_by_user:
                raise ValueError(
                    "The name of the user is required."
                )

            # Check that the selected ward belongs to the LGA
            cursor.execute(
                """
                SELECT
                    uniqueid,
                    ward_id
                FROM ward
                WHERE uniqueid = %s
                  AND lga_id = %s
                """,
                (ward_uniqueid, lga_id)
            )

            selected_ward = cursor.fetchone()

            if selected_ward is None:
                raise ValueError(
                    "The selected ward does not belong "
                    "to the selected LGA."
                )

            # Generate the next polling unit ID inside the ward
            cursor.execute(
                """
                SELECT
                    COALESCE(MAX(polling_unit_id), 0) + 1
                    AS next_polling_unit_id
                FROM polling_unit
                WHERE lga_id = %s
                  AND ward_id = %s
                """,
                (lga_id, selected_ward["ward_id"])
            )

            next_polling_unit_id = cursor.fetchone()[
                "next_polling_unit_id"
            ]

            user_ip_address = (
                request.remote_addr or "127.0.0.1"
            )

            # Create the new polling unit
            cursor.execute(
                """
                INSERT INTO polling_unit (
                    polling_unit_id,
                    ward_id,
                    lga_id,
                    uniquewardid,
                    polling_unit_number,
                    polling_unit_name,
                    polling_unit_description,
                    entered_by_user,
                    date_entered,
                    user_ip_address
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    %s
                )
                """,
                (
                    next_polling_unit_id,
                    selected_ward["ward_id"],
                    lga_id,
                    ward_uniqueid,
                    polling_unit_number,
                    polling_unit_name,
                    polling_unit_description,
                    entered_by_user,
                    user_ip_address
                )
            )

            new_polling_unit_id = cursor.lastrowid
            party_results = []

            # Validate and prepare one result for every party
            for party in parties:
                party_abbreviation = party[
                    "party_abbreviation"
                ]

                score = int(
                    request.form.get(
                        f"score_{party_abbreviation}",
                        ""
                    )
                )

                if score < 0:
                    raise ValueError(
                        "Party scores cannot be negative."
                    )

                party_results.append(
                    (
                        str(new_polling_unit_id),
                        party_abbreviation,
                        score,
                        entered_by_user,
                        user_ip_address
                    )
                )

            # Save all party results in one database operation
            cursor.executemany(
                """
                INSERT INTO announced_pu_results (
                    polling_unit_uniqueid,
                    party_abbreviation,
                    party_score,
                    entered_by_user,
                    date_entered,
                    user_ip_address
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    %s
                )
                """,
                party_results
            )

            connection.commit()
            redirect_polling_unit_id = new_polling_unit_id

        except (ValueError, mysql.connector.Error) as error:
            connection.rollback()

            error_message = (
                f"Unable to save the results: {error}"
            )

    cursor.close()
    connection.close()

    if redirect_polling_unit_id is not None:
        return redirect(
            url_for(
                "new_polling_unit",
                created=redirect_polling_unit_id
            )
        )

    return render_template(
        "new_polling_unit.html",
        lgas=lgas,
        parties=parties,
        created_polling_unit_id=created_polling_unit_id,
        error_message=error_message
    )


if __name__ == "__main__":
    app.run(debug=True)