<!DOCTYPE html>
<html lang="en">
<body>
  <?php
  $servername = "localhost";
  $username = "username";
  $password = "password";
  $dbname = "myDB";

  $conn = new mysqli($servername, $username, $password, $dbname);

  if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
  }

  $sql = "SELECT id, username, favorite_song, artist FROM InsertTableName WHERE username = "insert_name";
  $result = $conn->query($sql);

  if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
      echo "<br> id: ". $row["id"]. " - Name: ". $row["username"]. " " . $row["favorite_song"] . " " $row["artist"]. "<br>";
    }
  } else {
    echo "0 results";
  }

  $conn->close();
  ?>
</body>
</html>
