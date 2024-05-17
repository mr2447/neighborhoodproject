-- REGISTER NEW USER CREATE USER TABLE
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL,
    profile_text TEXT,
    photo_url VARCHAR(255)
);
-- PREEXISTING DIVISIONS 
CREATE TABLE Neighborhoods (
    neighborhood_id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    description TEXT
);
--  PREEXISTING DIVISIONS 
CREATE TABLE Blocks (
    block_id SERIAL PRIMARY KEY,
    neighborhood_id INT NOT NULL,
    name VARCHAR (200) NOT NULL,
    description VARCHAR (200),
    latitude FLOAT,
    longitude FLOAT,
    radius FLOAT, 
    -- column location geography(Point, 4326),
    -- use postgres extension for radius
    FOREIGN KEY (neighborhood_id) REFERENCES Neighborhoods(neighborhood_id)
);


-- ALTER TABLE Blocks
-- ADD COLUMN location geography(Point, 4326);

-- USERS should apply for block membership
-- A table of all the users and thier associated blocks
-- have a function that checks if user is in membership
CREATE TABLE Block_Memberships (
    membership_id SERIAL PRIMARY KEY,
    block_id INT NOT NULL,
    user_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL CHECK (status IN ('active', 'in-active')),
    join_date DATE NOT NULL,
    -- if membership canceled.
    update_date Date NOT NULL,
    FOREIGN KEY (block_id) REFERENCES Blocks(block_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- FRIENDSHIP TABLE, user and user relationships
-- have a function that returns true if freindship exists
CREATE TABLE Friendships (
    user_id1 INT NOT NULL,
    user_id2 INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id1) REFERENCES Users(user_id),
    FOREIGN KEY (user_id2) REFERENCES Users(user_id),

    -- Ensure unique pairs
    CONSTRAINT unique_user_pairs UNIQUE (user_id1, user_id2)
);




CREATE TABLE Neighbors (
    neighbor_id1 INT NOT NULL,
    neighbor_id2 INT NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (neighbor_id1) REFERENCES Users(user_id),
    FOREIGN KEY (neighbor_id2) REFERENCES Users(user_id),
    UNIQUE (neighbor_id1, neighbor_id2)
);

-- click new THREAD to create a thread
-- cotains all the origial messeges 
CREATE TABLE Threads (
    thread_id SERIAL PRIMARY KEY,
    -- don't need the original message id since there is none at creation
    original_message_id INT,
    -- specify the relationship who you'd like this to go to
    recipient_type VARCHAR(20) NOT NULL CHECK (recipient_type IN ('Friend', 'Neighbor', 'Block')),
    -- if References block_id, then we query all the users who are in that block_id and display the message to them
    -- if References user_id, then we query that specific friend 
    -- if References neighbor, then we query all users who are in a neighborhood. 
    recipient_id INT NOT NULL,
    -- user_id where block, freind, or neighbor is a condition. ie if user_id.freind = true
    FOREIGN KEY (recipient_id) REFERENCES Users(user_id), 
    FOREIGN KEY (original_message_id) REFERENCES Messages(message_id)
);

-- Message table, contains all the messeages 
CREATE TABLE Messages (
    message_id  SERIAL PRIMARY KEY,
    thread_id INT NOT NULL,
    reply_to INT,
    send_to INT,
    title VARCHAR(200),
    body TEXT NOT NULL,
    author_id INT NOT NULL,
    location TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (send_to) REFERENCES Users(user_id),
    FOREIGN KEY (reply_to) REFERENCES Users(user_id),
    FOREIGN KEY (author_id) REFERENCES Users(user_id)
);

-- When a recipient recieve a messege ie got a send_to user_ID match, create this table default to unread.
--Update to read when they click open it. 
CREATE TABLE Read_Status_Recorder (
    read_status_id SERIAL PRIMARY KEY,
    reader_id INT,
    message_id INT,
    status VARCHAR(20) DEFAULT 'Unread' CHECK (status IN ( 'Read', 'Unread')),
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES Messages(message_id),
    FOREIGN KEY (reader_id) REFERENCES Users(user_id)
);

-- if SUM(Votes(status))>=3, then Application(status) = approved
CREATE TABLE Application (
    application_id SERIAL PRIMARY KEY,
    block_id INT NOT NULL,
    applicant_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date date,
    FOREIGN KEY (block_id) REFERENCES Blocks(block_id),
    FOREIGN KEY (applicant_id) REFERENCES Users(user_id)
);

-- Use group by to count the votes
CREATE TABLE Votes (
    application_id INT NOT NULL,
    voter_id INT NOT NULL,
    -- plus 1
    vote_count INT
    FOREIGN KEY (voter_id) REFERENCES Users(user_id),
    FOREIGN KEY (application_id) REFERENCES Application(application_id),
    -- each voter can vote once for each application
    PRIMARY KEY (application_id, voter_id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
--##################################################################################################################
--##################################################################################################################
--##################################################################################################################
--##################################################################################################################

-- C1
-- ALLOW USER TO SIGN-UP
INSERT INTO Users (username, email, password_hash, address, profile_text, photo_url) VALUES 
('Logan_grey', 'logan.grey@example.com', 'hashpassword11', '104 Royal St, Beachside', 'Politician', 'http://example.com/photos/logangrey.jpg');

-- APPLY to block 
-- FETCH BLOCK_ID FROM Blocks WHERE block name is block D2 -> 8
-- FETCH Applicant_id from Users WHERE username is Logan Grey -> 11
-- status default value is 'pending'
-- created_date default to CURRENT_DATE
INSERT INTO Application (block_id, applicant_id) VALUES 
(8, 11);
-- UPDATE USER PROFILE
UPDATE Users
SET email = 'newLogan.grey@example.com', address = '456 New Address St, New City'
WHERE user_id = 11;  -- Assuming you know the user's ID is 11
-- DELETE USERS maybe don't allow this option
DELETE FROM Users
WHERE user_id = 11;  -- Replace '1' with the actual user ID of the user you want to delete

-- CLICK 'create new thread'
-- Get 'type' by selecting buttons ('personal' or 'neighbor' or 'block')
--fetch recipient_id (user_id) via email if type = friend or
--fetch recipient_id(neighborhood_id) via email if type = neighbor or
-- fetch recipient_id (block_id) via block.name if type = block
-- The query will only query the user with the same recipient_type to show them the message.
INSERT INTO Threads (recipient_type, recipient_id) Values ('friend', '1')
-- RETURNING thread_id;

-- FETCH RETURNING thread_id from previously created thread
-- FETCH recipient_id from thread as send_to
--AUTHOR is the current user 

INSERT INTO Messages (thread_id, send_to, title, body, author_id, location) VALUES 
(1, 1, 'Hello again yo', 'Hello, a new thread from test1 to john doe', 15, 'New City');

-- userId = 1 is going to reply to 11 under the same thread
-- this text box will only show messages with the same thread_id
INSERT INTO Messages (thread_id, send_to, title, body, author_id, location) VALUES
(11, 11, 'Hello back', 'Hello new user, I am the first user', 1, 'New City');

-- make friend request
-- user_id1 requests user_id2
-- if user_id2 accepts, it updates this instance to accepted. 
INSERT INTO Friendships (user_id1, user_id2) VALUES 
(1,11);
-- Update to accepted freidnships
-- if someone got rejected, you can no longer request, unless the other person request you.
UPDATE Friendships
SET status = 'accepted', 
    update_date = CURRENT_TIMESTAMP
WHERE user_id1 = 1 
  AND user_id2 = 11
-- ALL 15's current pending requests
SELECT * 
FROM Friendships f
JOIN Users u ON u.user_id = f.user_id1
WHERE f.user_id2 = 15
AND status = 'pending';


-- neighbor does not need to accept 
-- just need to make this connection to potentially see threads
INSERT INTO neighbors (neighbor_id1, neighbor_id2) VALUES 
(1,11);
--##################################################################################################################
-- list all friends of user_id = 11
SELECT 
    CASE 
        WHEN f.user_id1 = 11 THEN f.user_id2 
        ELSE f.user_id1 
    END AS friend_id,
    u.username,
    f.status,
    f.created_date,
    f.update_date
FROM Friendships f
JOIN Users u ON u.user_id = CASE 
                               WHEN f.user_id1 = 11 THEN f.user_id2 
                               ELSE f.user_id1 
                           END
WHERE (11 = f.user_id1 OR 11 = f.user_id2)
  AND f.status = 'accepted';
-- return just the user_ids of friends
SELECT 
    CASE 
        WHEN f.user_id1 = 11 THEN f.user_id2 
        ELSE f.user_id1 
    END AS friend_id
FROM Friendships f
WHERE (11 = f.user_id1 OR 11 = f.user_id2)
  AND f.status = 'accepted';
--##################################################################################################################
-- recorder
-- display all messages where its read_recorder status is unread. 
INSERT INTO Read_status_recorder (reader_id, message_id) Values 
(1, 1),
(11, 2);
-- Update
UPDATE Read_status_recorder
SET status = 'Read', 
    updated_at = CURRENT_TIMESTAMP
WHERE reader_id = 1 
  AND message_id = 1;
--##################################################################################################################
-- SHOW ONLY UNREAD MESSAGES TO USER ID 11
SELECT * FROM Messages
JOIN read_status_recorder ON Messages.send_to = 11
WHERE read_status_recorder.status = 'Unread';
--##################################################################################################################
-- SHow only unread message to and from user ID 11 FROM and TO user 11's freinds
SELECT m.message_id 
FROM Messages m 
JOIN read_status_recorder r ON m.message_id = r.message_id
JOIN (
        SELECT 
            CASE
                WHEN f.user_id1 = 11 THEN f.user_id2
                ELSE f.user_id1
            END AS friend_id
        FROM Friendships f
        WHERE 11 IN (f.user_id1, f.user_id2)
            AND f.status = 'accepted'
) friends ON (m.send_to = friends.friend_id AND m.author_id = 11)
OR (m.author_id = friends.friend_id AND m.send_to = 11)

Where r.status = 'Unread';

--##################################################################################################################
-- search messages.body for text such as "Hello back" in all User 11 that He can access
-- can access all his friends, all his neighbor, all his block, all his neighborhood
-- friend=accepted, block = active, neighbor?

-- INSERT NEIGHBORS
INSERT INTO Neighbors (neighbor_id1, neighbor_id2, created_date, update_date)
VALUES (1, 11, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
-- SELECT ALL user11's neighbors
-- IF users want to send messages to neighbor, they must be the neighbor_id2.
-- SO neighbor_id1 has to set up their neighbor relationship
-- IF user want to recieve message from their neightbor, they must be the neighbor_id1 
-- so neighbor_id1 has to set up their neighbor relationship
-- user1 can set up and recieve
-- user2 can only send 
-- It is a one way system, so that if user recieved a messagem it is his own wishes and if user wants to send, he has to get the neighbor to establish that relationship in-person.
SELECT u.user_id, n.neighbor_id2 FROM Users u
JOIN neighbors n ON u.user_id = n.neighbor_id1
WHERE u.user_id =1

--##################################################################################################################
-- all friend, all neighbor, all block containing a sentence like "Hello back "
-- SELECT all users with the same block_id as user 1
-- each relationship join is a LEFT JOIN, allowing for a NULL result if the relationship condition is not met. 
SELECT DISTINCT bm.user_id
FROM Block_Memberships bm
JOIN Block_Memberships bm2 ON bm.block_id = bm2.block_id
WHERE bm2.user_id = 1;

SELECT m.message_id 
FROM Messages m 
JOIN read_status_recorder r ON m.message_id = r.message_id
LEFT JOIN (
    SELECT 
        CASE
            WHEN f.user_id1 = 1 THEN f.user_id2
            ELSE f.user_id1
        END AS friend_id
    FROM Friendships f
    WHERE 1 IN (f.user_id1, f.user_id2)
        AND f.status = 'accepted'
) friends ON (m.send_to = friends.friend_id AND m.author_id = 1)
    OR (m.author_id = friends.friend_id AND m.send_to = 1)
LEFT JOIN (
    SELECT DISTINCT bm.user_id
    FROM Block_Memberships bm
    JOIN Block_Memberships bm2 ON bm.block_id = bm2.block_id
    WHERE bm2.user_id = 1
) blocks ON (m.send_to = blocks.user_id AND m.author_id = 1)
    OR (m.author_id = blocks.user_id AND m.send_to = 1)
LEFT JOIN (
    SELECT u.user_id, n.neighbor_id1, n.neighbor_id2 
    FROM Users u
    JOIN neighbors n ON u.user_id = n.neighbor_id1
    WHERE u.user_id = 1
) neighbors ON (m.send_to = neighbors.neighbor_id1 AND m.author_id = 1)
    OR (m.author_id = neighbors.neighbor_id2 AND m.send_to = 1)
WHERE r.status = 'Unread' 
    AND LOWER(body) LIKE LOWER('%Hello %')
    AND (friends.friend_id IS NOT NULL OR blocks.user_id IS NOT NULL OR neighbors.user_id IS NOT NULL);

--##################################################################################################################
-- LOCATION LONGITUDELATITUDe 
-- CREATE EXTENSION postgis;

-- CREATE TABLE blocks_area (
--     blocks_area_id SERIAL PRIMARY KEY,
--     geom GEOMETRY(Point, 4326)
-- );
-- -- Insert latitude and longitude values into the location column
-- UPDATE Blocks
-- SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);

-- --FILTER DISTNACES
-- SELECT *
-- FROM Messages
-- WHERE ST_DWithin(
--     location::geography, -- Cast the location column to geography type
--     ST_SetSRID(ST_MakePoint(-73.9857, 40.7484), 4326)::geography, -- Cast the point to geography type
--     200 -- Distance in meters
-- );

-- ALL not freinds with user_id=15
SELECT *
FROM Users
WHERE user_id != 15
AND user_id NOT IN (
    SELECT CASE
               WHEN user_id1 = 15 THEN user_id2
               ELSE user_id1
           END AS friend_id
    FROM Friendships
    WHERE user_id1 = 15 OR user_id2 = 15
);

-- SELECT * FROM neighbors n, user_id2 is the neighbor, user_id1 is you the user
SELECT * FROM neighbors n
JOIN Users u ON n.neighbor_id2 = u.user_id
-- all who are not neighbors of user 15
SELECT *
FROM Users
WHERE user_id != 15
AND user_id NOT IN (
    SELECT neighbor_id2
    FROM Neighbors
    WHERE neighbor_id1 = 15
);


-- not firiend or no data. dont want accepted or pending
SELECT *
FROM Users
WHERE user_id != 15
AND user_id NOT IN (
    SELECT CASE
        WHEN user_id1 = 15 THEN user_id2
        ELSE user_id1
    END AS friend_id
    FROM Friendships
    WHERE (user_id1 = 15 OR user_id2 = 15)
    AND status IN ('accepted', 'pending')
)

UNION

SELECT u.*
FROM Users u
JOIN Friendships f ON u.user_id = CASE
    WHEN f.user_id1 = 15 THEN f.user_id2
    ELSE f.user_id1
END
WHERE (f.user_id1 = 15 OR f.user_id2 = 15)
AND f.status = 'rejected';

-- Delete friend relationshp
DELETE FROM Friendships
WHERE user_id1 = 7 AND user_id2 = 15;

-- create new thead
INSERT INTO Threads (recipient_type, recipient_id) 
            VALUES ('Friend', (SELECT user_id FROM Users WHERE email = 'john.doe@example.com')) 
            -- RETURNING thread_id

-- check voting eligibility
SELECT v.*
FROM Votes v
JOIN Block_Memberships bm ON v.voter_id = bm.user_id
JOIN Application a ON v.application_id = a.application_id
WHERE bm.block_id = a.block_id
AND bm.status = 'active';

-- insert block_membership
INSERT INTO Block_Memberships (block_id, user_id, status, join_date, update_date)
 VALUES (2, 16, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)