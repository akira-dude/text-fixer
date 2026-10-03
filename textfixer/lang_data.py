"""Frequent words used to train tiny bigram models for layout detection."""

RU_WORDS = """
и в не на я что он с как а то это все она так его но да ты к у же вы за бы по
только ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли
если уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя
ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без
будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой
совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда зачем всех
никогда можно при наконец два об другой хоть после над больше тот через эти
нас про всего них какая много разве три эту моя впрочем хорошо свою этой перед
иногда лучше чуть том нельзя такой им более всегда конечно всю между привет
спасибо пожалуйста давай сегодня завтра вчера сделать делать знаю знать думаю
хочу хочешь можешь могу нужно время работа работаю человек люди день ночь утро
вечер дома домой говорит сказал сказать понял понятно смотри посмотри слушай
пиши напиши скинь скину отправь отправил получил получилось проблема вопрос
ответ очень просто правда сколько почему кстати вообще короче ладно окей ок
нормально класс круто жаль вроде типа ребята друг брат игра играть сервер код
задача сделал сделали буду будем будешь пойдем пошли идти иду приду пришел
минут часов неделю месяц год деньги видел видишь случае место город страна
новый новая новое старый большой маленький хороший плохой первый последний
другие такие которые который которая которое своей своего моего твой твоя твое
нашего наш наша ваш ваша писать читать работать звонить позвони жду ждать
понимаю понимаешь помоги помочь давно скоро сразу вместе отлично согласен
согласна ошибка исправить написал написала сообщение текст раскладка клавиатура
компьютер телефон интернет вопросы спросить ответить ответил долго быстро
медленно поздно рано дела люблю тебе тобой мною нам ними вами всем пока его
хотел хотела знаешь думаешь кажется наверное точно вот-вот сам сама сами весь
вся всё ещё уже где-то тоже какие каждый любой нужен нужна надеюсь получится
смогу сможешь давайте здравствуйте извините прости спокойной ночи доброе утро
день вечер неплохо пожалуй значит например вместо около вокруг снова надо было
"""

EN_WORDS = """
the be to of and a in that have i it for not on with he as you do at this but
his by from they we say her she or an will my one all would there their what so
up out if about who get which go me when make can like time no just him know
take people into year your good some could them see other than then now look
only come its over think also back after use two how our work first well way
even new want because any these give day most us is are was were been has had
did does said got going im dont cant thats yes yeah ok okay hello hi hey thanks
thank please sorry sure right really very much more here why where today
tomorrow yesterday need help maybe still never always something nothing
everything someone game play server code message send sent text check fix done
let lets great nice cool love man guys friend wait sec minute later soon
morning night call talk meet youll ill well its should must might again too
ever every each many few last long little own same big high different small
large next early young important public bad able world life hand part child eye
woman place week case point company number group problem fact keyboard layout
computer phone internet question answer write read wrong correct wanted tried
trying working thing things guess mean feel find tell ask seem try leave put
old home house before while through down off around another show lol bro wow
github http https www com update build test run file folder bug issue commit
"""


def words(raw: str) -> list[str]:
    return [w for w in raw.split() if w]
