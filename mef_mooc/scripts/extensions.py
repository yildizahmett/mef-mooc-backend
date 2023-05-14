from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
import redis
from mef_mooc.config import REDIS_HOST, REDIS_PORT, REDIS_DB

jwt = JWTManager()
bcrypt = Bcrypt()

jwt_redis_blocklist = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )

@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    token_in_redis = jwt_redis_blocklist.get(jti)
    return token_in_redis is not None